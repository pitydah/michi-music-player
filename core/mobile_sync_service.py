"""MobileSyncService — pairing, trust, and mobile sync with the Michi app.

Slice 7 (ADR-002): the service is REAL:

- Paired devices persist in the library database (``mobile_sync_devices``,
  migration 8). In-memory state is only a cache loaded at construction.
- ``start()``/``stop()`` own the real listener lifecycle: the production HTTP
  handler (``SyncRequestHandler`` from ``sync/sync_server.py``) mounted with
  the Michi Link v1 routes (``MichiLinkServer``), served on a daemon thread.
- ``health()`` is truthful: ``server_listening`` is a live socket probe,
  never an assumption. When no listener runs, it reports ``False``.
- Pairing sessions are one-time and in-memory by design (they expire after
  ``_pairing_timeout``); trust/revocation are persistent. Proof of possession
  (challenge/response) is enforced whenever the device presents a public key.
- Rate limiting uses in-memory per-IP counters (documented: counters reset on
  process restart; the server-side handler also rate-limits independently).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import logging
import secrets
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger("michi.mobile_sync")

_PAIRING_TIMEOUT = 300  # 5 minutes
_MAX_VERIFY_ATTEMPTS = 5
_RATE_WINDOW_SECONDS = 300.0
_DEFAULT_PORT = 28700
QR_PAYLOAD_VERSION = "1"


@dataclass
class PairedDevice:
    device_id: str
    name: str
    public_key: str = ""
    fingerprint: str = ""
    paired_at: float = 0.0
    last_seen: float = 0.0
    trusted: bool = False
    revoked: bool = False
    protocol_version: str = "1.0"


@dataclass
class PairingSession:
    session_id: str
    code: str
    challenge: str = ""
    created_at: float = 0.0
    expires_at: float = 0.0
    verified: bool = False
    device_id: str = ""


class _CallbackSignal:
    """Minimal signal shim for the listener (no Qt dependency)."""

    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, slot) -> None:
        self._slots.append(slot)

    def emit(self, *args, **kwargs) -> None:
        for slot in list(self._slots):
            try:
                slot(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - listener must survive
                logger.debug("Listener signal slot failed: %s", exc)


class _Listener:
    """Real HTTP listener: SyncRequestHandler + Michi Link v1 routes.

    Mirrors ``SyncServer``'s wiring (device registry, sessions, track index,
    manifest providers) but runs on a plain daemon thread so the service can
    start/stop it without a Qt event loop. The same handler class serves
    ``/api/*`` (sync) and ``/api/v1/*`` (Michi Link) endpoints.
    """

    def __init__(self, db, port: int, alias: str = "Michi Music Player",
                 registry=None, pairing_service=None) -> None:
        self._db = db
        self._port = port
        self._alias = alias
        self._device_registry = registry
        self._pairing_service = pairing_service
        self._httpd = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._sessions: dict[str, object] = {}
        self._sessions_lock = threading.Lock()
        self._track_index: dict[str, str] = {}
        self._track_index_built = False
        self._manifest_provider = None
        self._delta_provider = None
        self._local_account = None
        self._import_store = None
        self.client_connected = _CallbackSignal()
        self.sync_error = _CallbackSignal()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def port(self) -> int:
        return self._port

    @property
    def sessions(self) -> dict[str, object]:
        return self._sessions

    def _build_index(self) -> None:
        if not self._db:
            return
        try:
            items = self._db.get_all()
        except Exception as exc:  # noqa: BLE001 - never crash the listener
            logger.debug("Track index build failed: %s", exc)
            return
        from sync.sync_protocol import make_track_id

        new_index = {}
        for item in items:
            fp = getattr(item, "filepath", "")
            tuid = getattr(item, "track_uid", "") if hasattr(item, "track_uid") else ""
            new_index[make_track_id(fp, tuid)] = fp
        self._track_index = new_index
        self._track_index_built = True

    def _resolve_track(self, track_id: str) -> str | None:
        if not self._track_index_built:
            self._build_index()
        return self._track_index.get(track_id)

    def _purge_expired_sessions(self) -> None:
        with self._sessions_lock:
            expired = [
                k for k, v in self._sessions.items()
                if getattr(v, "is_expired", lambda: False)()
            ]
            for k in expired:
                self._sessions.pop(k, None)

    def start(self) -> tuple[bool, str]:
        """Bind the listener. Returns (ok, error_message)."""
        if self._running:
            return True, ""
        self._build_index()

        from http.server import HTTPServer

        from sync.sync_server import SyncRequestHandler
        from integrations.michi_link.server import MichiLinkServer

        SyncRequestHandler.server_ref = self
        try:
            MichiLinkServer.mount(
                SyncRequestHandler,
                pairing_service=self._pairing_service,
            )
        except Exception as exc:  # noqa: BLE001 - mounting must not kill start
            logger.warning("MichiLinkServer mount failed: %s", exc)
        try:
            self._httpd = HTTPServer(("0.0.0.0", self._port), SyncRequestHandler)
        except OSError as exc:
            self._httpd = None
            return False, str(exc)
        if self._port == 0:
            self._port = int(self._httpd.server_address[1])
        self._httpd.timeout = 0.2
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return True, ""

    def _serve(self) -> None:
        purge_counter = 0
        while self._running and self._httpd is not None:
            try:
                self._httpd.handle_request()
                purge_counter += 1
                if purge_counter >= 50:
                    self._purge_expired_sessions()
                    purge_counter = 0
            except Exception as exc:  # noqa: BLE001 - keep serving
                if self._running:
                    self.sync_error.emit(str(exc))

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._httpd is not None:
            try:
                self._httpd.server_close()
            except Exception:  # noqa: BLE001 - best effort close
                logger.debug("Listener close failed", exc_info=True)
        self._httpd = None
        self._thread = None
        self._sessions.clear()


class MobileSyncService:
    def __init__(self, db=None, event_bus=None, registry=None, port: int = _DEFAULT_PORT):
        self._db = db
        self._event_bus = event_bus
        self._registry = registry
        self._server_port = self._clamp_port(port)
        self._pairing_timeout = _PAIRING_TIMEOUT
        self._paired_devices: dict[str, PairedDevice] = {}
        self._active_sessions: dict[str, PairingSession] = {}
        self._attempt_log: dict[str, list[float]] = {}
        self._last_error = ""
        self._last_sync = 0.0
        self._listener: _Listener | None = None
        self._load_devices()

    # ── Persistence ──

    @property
    def _persistence(self) -> str:
        return "db" if self._db is not None else "memory"

    def _load_devices(self) -> None:
        if self._db is None:
            return
        try:
            rows = self._db.conn.execute(
                "SELECT device_id, name, public_key, fingerprint, trusted, "
                "revoked, paired_at, last_seen, protocol_version "
                "FROM mobile_sync_devices"
            ).fetchall()
        except (sqlite3.OperationalError, sqlite3.DatabaseError, AttributeError) as exc:
            logger.warning("mobile_sync_devices table unavailable (%s); "
                           "pairing state is memory-only", exc)
            return
        for row in rows:
            device = PairedDevice(
                device_id=row[0], name=row[1], public_key=row[2] or "",
                fingerprint=row[3] or "", trusted=bool(row[4]),
                revoked=bool(row[5]), paired_at=row[6] or 0.0,
                last_seen=row[7] or 0.0, protocol_version=row[8] or "1.0",
            )
            self._paired_devices[device.device_id] = device
            self._last_sync = max(self._last_sync, device.last_seen)

    def _persist_device(self, device: PairedDevice) -> None:
        if self._db is None:
            return
        try:
            self._db.conn.execute(
                "INSERT OR REPLACE INTO mobile_sync_devices "
                "(device_id, name, public_key, fingerprint, trusted, revoked, "
                " paired_at, last_seen, protocol_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (device.device_id, device.name, device.public_key,
                 device.fingerprint, int(device.trusted), int(device.revoked),
                 device.paired_at, device.last_seen, device.protocol_version),
            )
            self._db.conn.commit()
        except (sqlite3.DatabaseError, AttributeError) as exc:
            logger.warning("Failed to persist paired device %s: %s",
                           device.device_id, exc)

    def _delete_device(self, device_id: str) -> None:
        if self._db is None:
            return
        try:
            self._db.conn.execute(
                "DELETE FROM mobile_sync_devices WHERE device_id=?",
                (device_id,))
            self._db.conn.commit()
        except (sqlite3.DatabaseError, AttributeError) as exc:
            logger.warning("Failed to delete paired device %s: %s",
                           device_id, exc)

    def _mark_seen(self, device_id: str) -> None:
        device = self._paired_devices.get(device_id)
        if not device:
            return
        device.last_seen = time.time()
        self._last_sync = max(self._last_sync, device.last_seen)
        self._persist_device(device)

    # ── Query API ──

    @property
    def paired_devices(self) -> list[PairedDevice]:
        return list(self._paired_devices.values())

    def is_paired(self, device_id: str) -> bool:
        return device_id in self._paired_devices

    def is_trusted(self, device_id: str) -> bool:
        d = self._paired_devices.get(device_id)
        return d is not None and d.trusted and not d.revoked

    # ── Pairing sessions ──

    def start_pairing(self) -> dict:
        session_id = secrets.token_hex(16)
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        now = time.time()
        session = PairingSession(
            session_id=session_id,
            code=code,
            challenge=secrets.token_hex(16),
            created_at=now,
            expires_at=now + self._pairing_timeout,
        )
        self._active_sessions[session_id] = session

        qr_data = (f"michi://pair?v={QR_PAYLOAD_VERSION}"
                   f"&session={session_id}&code={code}")
        qr_data_uri, mime = self._generate_qr(qr_data)
        return {"ok": True, "session_id": session_id, "code": code,
                "qr_payload": qr_data, "qr_data_uri": qr_data_uri,
                "qr_mime_type": mime,
                "qr_data": qr_data,  # deprecated alias, removed in S8
                "qr_svg": qr_data_uri,  # deprecated alias, removed in S8
                "expires_at": session.expires_at}

    def _generate_qr(self, data: str) -> tuple[str, str]:
        """Render a QR payload. Returns (data_uri, mime_type); empty when the
        qrcode package is not installed (callers must surface this)."""
        try:
            import qrcode

            qr = qrcode.make(data)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            encoded = base64.b64encode(buf.getvalue()).decode()
            return "data:image/png;base64," + encoded, "image/png"
        except ImportError:
            return "", ""

    def get_qr_code(self, session_id: str) -> dict:
        session = self._active_sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "SESSION_NOT_FOUND"}
        qr_data = (f"michi://pair?v={QR_PAYLOAD_VERSION}"
                   f"&session={session_id}&code={session.code}")
        qr_data_uri, mime = self._generate_qr(qr_data)
        return {"ok": True, "qr_payload": qr_data,
                "qr_data_uri": qr_data_uri, "qr_mime_type": mime,
                "qr_data": qr_data,  # deprecated alias, removed in S8
                "qr_svg": qr_data_uri}  # deprecated alias, removed in S8

    def get_pairing_challenge(self, session_id: str) -> dict:
        """Issue the proof-of-possession challenge for a pairing session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "SESSION_NOT_FOUND"}
        if time.time() > session.expires_at:
            self._active_sessions.pop(session_id, None)
            return {"ok": False, "error": "SESSION_EXPIRED"}
        return {"ok": True, "challenge": session.challenge,
                "session_id": session_id}

    def _check_rate_limit(self, key: str) -> bool:
        now = time.time()
        attempts = [t for t in self._attempt_log.get(key, [])
                    if now - t < _RATE_WINDOW_SECONDS]
        self._attempt_log[key] = attempts
        return len(attempts) < _MAX_VERIFY_ATTEMPTS

    def _record_attempt(self, key: str) -> None:
        self._attempt_log.setdefault(key, []).append(time.time())

    def verify_pairing(self, session_id: str, code: str, device_name: str = "",
                       device_id: str = "", public_key: str = "",
                       fingerprint: str = "", proof: str = "",
                       ip: str = "") -> dict:
        """Complete a pairing session.

        A device that presents a public key or fingerprint MUST prove
        possession of the code via ``proof`` = HMAC-SHA256(code, challenge);
        otherwise pairing is rejected. Code-only pairing is accepted for
        legacy clients, but never yields a persistent key record.
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "SESSION_NOT_FOUND"}
        if time.time() > session.expires_at:
            self._active_sessions.pop(session_id, None)
            return {"ok": False, "error": "SESSION_EXPIRED"}
        rate_key = ip or device_id or session_id
        if not self._check_rate_limit(rate_key):
            return {"ok": False, "error": "RATE_LIMITED"}
        if session.code != code:
            self._record_attempt(rate_key)
            return {"ok": False, "error": "INVALID_CODE"}

        if public_key or fingerprint:
            expected = hmac.new(
                code.encode(), session.challenge.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not proof or not hmac.compare_digest(proof, expected):
                self._record_attempt(rate_key)
                return {"ok": False, "error": "PROOF_INVALID"}

        session.verified = True
        if device_id:
            did = device_id
        elif fingerprint:
            did = fingerprint[:24]
        else:
            did = hashlib.sha256(
                f"{session_id}:{device_name}:{public_key}".encode()
            ).hexdigest()[:16]
        now = time.time()
        device = PairedDevice(
            device_id=did,
            name=device_name or "Mobile Device",
            public_key=public_key,
            fingerprint=fingerprint,
            paired_at=now,
            last_seen=now,
            trusted=True,
            protocol_version=QR_PAYLOAD_VERSION,
        )
        self._paired_devices[did] = device
        self._persist_device(device)
        self._last_sync = now
        self._active_sessions.pop(session_id, None)
        return {"ok": True, "device_id": did, "device_name": device.name}

    def unpair(self, device_id: str) -> dict:
        device = self._paired_devices.get(device_id)
        if device is None:
            return {"ok": False, "error": "NOT_FOUND"}
        self._paired_devices.pop(device_id, None)
        self._delete_device(device_id)
        return {"ok": True}

    def trust_device(self, device_id: str) -> dict:
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        d.trusted = True
        d.revoked = False
        self._persist_device(d)
        return {"ok": True}

    def revoke_trust(self, device_id: str) -> dict:
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        d.trusted = False
        d.revoked = True
        self._persist_device(d)
        return {"ok": True}

    def get_pairing_info(self, device_id: str) -> dict | None:
        d = self._paired_devices.get(device_id)
        if not d:
            return None
        return {"device_id": d.device_id, "name": d.name,
                "public_key": d.public_key, "fingerprint": d.fingerprint,
                "paired_at": d.paired_at, "last_seen": d.last_seen,
                "trusted": d.trusted, "revoked": d.revoked,
                "protocol_version": d.protocol_version}

    def get_pending_sessions(self) -> list[dict]:
        now = time.time()
        active = []
        expired = []
        for sid, s in self._active_sessions.items():
            if now > s.expires_at:
                expired.append(sid)
            else:
                active.append({"session_id": sid, "created_at": s.created_at,
                               "expires_at": s.expires_at,
                               "verified": s.verified,
                               "has_challenge": bool(s.challenge)})
        for sid in expired:
            self._active_sessions.pop(sid, None)
        return active

    # ── Listener lifecycle ──

    @staticmethod
    def _clamp_port(port: int) -> int:
        """Clamp to the valid range; 0 means an ephemeral port (tests)."""
        if port == 0:
            return 0
        return max(1024, min(65535, port))

    def set_port(self, port: int):
        self._server_port = self._clamp_port(port)

    def get_port(self) -> int:
        return self._server_port

    @property
    def listening_port(self) -> int:
        """The port the listener is actually bound to (0 when not running)."""
        if self._listener is not None:
            return self._listener.port
        return 0

    def start(self) -> dict:
        """Start the real listener (sync + Michi Link v1 routes)."""
        if self._listener is not None and self._listener.is_running:
            return {"ok": True, "already_running": True,
                    "port": self._listener.port}
        from core.sync.device_registry import DeviceRegistry

        registry = self._registry or DeviceRegistry()
        listener = _Listener(
            db=self._db, port=self._server_port,
            registry=registry, pairing_service=self,
        )
        ok, error = listener.start()
        if not ok:
            self._last_error = error or "LISTENER_START_FAILED"
            return {"ok": False, "error": "LISTENER_START_FAILED",
                    "detail": self._last_error}
        self._listener = listener
        self._last_error = ""
        return {"ok": True, "port": listener.port, "listening": True}

    def stop(self) -> dict:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        return {"ok": True}

    def shutdown(self) -> None:
        """Container shutdown hook (stops the listener)."""
        self.stop()

    def is_listening(self) -> bool:
        """Truthful live probe: True only when a socket answers on our port."""
        if self._listener is None or not self._listener.is_running:
            return False
        port = self._listener.port
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            return False

    # ── Health ──

    def health(self) -> dict:
        return {
            "protocol_supported": QR_PAYLOAD_VERSION,
            "server_configured": True,
            "server_listening": self.is_listening(),
            "tls_available": False,
            "port": self.listening_port or self._server_port,
            "paired_devices": len(self._paired_devices),
            "trusted_devices": sum(
                1 for d in self._paired_devices.values()
                if d.trusted and not d.revoked),
            "revoked_devices": sum(
                1 for d in self._paired_devices.values() if d.revoked),
            "active_connections": (
                len(self._listener.sessions)
                if self._listener is not None else 0),
            "last_sync": self._last_sync,
            "last_error": self._last_error,
            "persistence": self._persistence,
            "paired": len(self._paired_devices),
            "active_sessions": len([
                s for s in self._active_sessions.values()
                if time.time() <= s.expires_at]),
        }
