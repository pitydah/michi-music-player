"""MobileSyncService — pairing, trust, and mobile sync with the Michi app.

Slice 7 (ADR-002) + Phase 7 (P0 stabilization, falso éxito #9):

- Paired devices persist in the library database (``mobile_sync_devices``,
  migration 8). In-memory state is only a cache loaded at construction.
- Pairing is a REAL challenge-response protocol (Ed25519 via the
  ``cryptography`` package when available):

    1. ``start_pairing()`` issues a session with a one-time ``nonce``.
    2. The device sends its public key.
    3. The device signs ``protocol_version|session_id|nonce|fingerprint|
       device_id`` with its private key.
    4. The server verifies the signature against the presented public key.
    5. The fingerprint is DERIVED server-side from the public key material
       (SHA-256); a client-supplied fingerprint is only *compared*, never
       trusted — mismatch is rejected (``FINGERPRINT_MISMATCH``).
    6. The device is created as ``awaiting_approval`` (trusted=False).
    7. ``approve_device()`` persists the device as trusted.

- Legacy code-only pairing (6-digit code, no signature) is OFF by default.
  When enabled (``legacy_code_pairing_enabled=True``) it is: loopback-only
  unless ``allow_lan_pairing``; NEVER auto-trusted (manual approval);
  TTL 5 minutes; recorded as an ``legacy_code_pairing`` audit entry; flagged
  as insecure in ``health()``.
- Persistence failure invalidates pairing: the device is never kept trusted
  in memory when the DB write fails (``PERSISTENCE_FAILED``).
- ``start()``/``stop()`` own the real listener lifecycle: the production HTTP
  handler (``SyncRequestHandler`` from ``sync/sync_server.py``) mounted with
  the Michi Link v1 routes (``MichiLinkServer``), served on a daemon thread.
  The handler reference is instance-held (per-request factory) — no global
  class state — and Michi Link routes must be mounted BEFORE the listener is
  declared operational (``ROUTES_NOT_MOUNTED`` otherwise).
- The canonical ``DeviceRegistry`` (``core/sync/device_registry.py``) is
  injected; the service never fabricates one.
- Rate limiting uses in-memory per-IP counters (documented: counters reset on
  process restart; the server-side handler also rate-limits independently).
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
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
_LEGACY_TTL = 300  # legacy code-only sessions: 5 minutes
_MAX_VERIFY_ATTEMPTS = 5
_RATE_WINDOW_SECONDS = 300.0
_DEFAULT_PORT = 28700
_DEFAULT_BIND_HOST = "127.0.0.1"
_MAX_AUDIT_ENTRIES = 200
QR_PAYLOAD_VERSION = "1"


def _parse_ed25519_public_key(key_material: str) -> bytes | None:
    """Return the raw 32-byte Ed25519 public key, or None if unparseable.

    Accepts either raw base64 (32 bytes) or PEM (SubjectPublicKeyInfo).
    """
    if not key_material:
        return None
    try:
        raw = base64.b64decode(key_material, validate=True)
        if len(raw) == 32:
            return raw
    except Exception:  # noqa: BLE001 - fall through to PEM
        pass
    try:
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
            load_pem_public_key,
        )

        pub = load_pem_public_key(key_material.encode())
        raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return raw if len(raw) == 32 else None
    except Exception:  # noqa: BLE001 - invalid key material
        return None


def _derive_fingerprint(raw_public_key: bytes) -> str:
    """Derive the device fingerprint server-side from public key material."""
    return hashlib.sha256(raw_public_key).hexdigest()


def _verify_ed25519_signature(raw_key: bytes, message: bytes,
                              signature_b64: str) -> bool:
    """Verify an Ed25519 signature over ``message``. Never raises."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )

        sig = base64.b64decode(signature_b64, validate=True)
        Ed25519PublicKey.from_public_bytes(raw_key).verify(sig, message)
        return True
    except Exception:  # noqa: BLE001 - verification failure is a False
        return False


def _signature_payload(protocol_version: str, session_id: str, nonce: str,
                       fingerprint: str, device_id: str) -> bytes:
    """Canonical signed payload — both sides must build it identically."""
    return (
        f"{protocol_version}|{session_id}|{nonce}|{fingerprint}|{device_id}"
    ).encode()




class _DeviceIdConflict:
    """Sentinel returned by _create_pending_device on key-swap conflict."""

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
    nonce: str = ""
    created_at: float = 0.0
    expires_at: float = 0.0
    verified: bool = False
    device_id: str = ""
    nonce_used: bool = False


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

    The handler reference is instance-held: a per-listener bound handler
    class assigns ``server_ref`` before the request is handled — no global
    class state (``BaseRequestHandler.__init__`` handles the request
    internally, so the binding must happen before ``super().__init__``).
    """

    def __init__(self, db, port: int, alias: str = "Michi Music Player",
                 registry=None, pairing_service=None,
                 bind_host: str = _DEFAULT_BIND_HOST,
                 import_store_path: str | None = None) -> None:
        self._db = db
        self._port = port
        self._alias = alias
        self._device_registry = registry
        self._pairing_service = pairing_service
        self._bind_host = bind_host
        self._import_store_path = import_store_path
        self._httpd = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._routes_mounted = False
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
    def bind_host(self) -> str:
        return self._bind_host

    @property
    def routes_mounted(self) -> bool:
        return self._routes_mounted

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

        try:
            MichiLinkServer.mount(
                SyncRequestHandler,
                pairing_service=self._pairing_service,
            )
        except Exception as exc:  # noqa: BLE001 - mounting must not kill start
            logger.warning("MichiLinkServer mount failed: %s", exc)
        if not getattr(SyncRequestHandler, "_michi_link_mounted", False):
            return False, "ROUTES_NOT_MOUNTED"
        self._routes_mounted = True

        # Instance-held reference: the request is handled INSIDE
        # BaseRequestHandler.__init__ (it calls self.handle()), so the
        # reference must be bound before super().__init__ — a post-init
        # factory would be too late. No global class state.
        listener = self

        class _BoundRequestHandler(SyncRequestHandler):
            def __init__(self, *args, **kwargs):
                self.server_ref = listener
                super().__init__(*args, **kwargs)

        try:
            self._httpd = HTTPServer(
                (self._bind_host, self._port), _BoundRequestHandler)
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
    def __init__(self, db=None, event_bus=None, registry=None,
                 device_registry=None, port: int = _DEFAULT_PORT,
                 bind_host: str = _DEFAULT_BIND_HOST,
                 allow_lan_pairing: bool = False,
                 tls_mode: str = "none",
                 allowed_networks: list[str] | None = None,
                 legacy_code_pairing_enabled: bool = False,
                 signature_pairing_enabled: bool = True,
                 import_store_path: str | None = None):
        self._db = db
        self._event_bus = event_bus
        self._registry = registry
        self._device_registry = device_registry or registry
        self._server_port = self._clamp_port(port)
        self._pairing_timeout = _PAIRING_TIMEOUT
        self._legacy_ttl = _LEGACY_TTL
        self._bind_host = bind_host or _DEFAULT_BIND_HOST
        self._allow_lan_pairing = allow_lan_pairing
        self._tls_mode = tls_mode or "none"
        self._allowed_networks = list(allowed_networks or [])
        self._legacy_code_pairing_enabled = legacy_code_pairing_enabled
        self._signature_pairing_enabled = signature_pairing_enabled
        self._import_store_path = import_store_path
        self._paired_devices: dict[str, PairedDevice] = {}
        self._active_sessions: dict[str, PairingSession] = {}
        self._attempt_log: dict[str, list[float]] = {}
        self._audit_log: list[dict] = []
        self._last_error = ""
        self._last_sync = 0.0
        self._listener: _Listener | None = None
        self._routes_mounted = False
        self._load_devices()

    @property
    def device_registry(self):
        """Public read port: the injected DeviceRegistry (single instance)."""
        return self._device_registry

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

    def _persist_device(self, device: PairedDevice) -> bool:
        """Persist a device; True on success (or memory-only persistence)."""
        if self._db is None:
            return True
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
            return True
        except (sqlite3.DatabaseError, AttributeError) as exc:
            logger.warning("Failed to persist paired device %s: %s",
                           device.device_id, exc)
            return False

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

    # ── Audit ──

    def _record_audit(self, kind: str, **fields) -> None:
        entry = {"kind": kind, "ts": time.time()}
        entry.update(fields)
        self._audit_log.append(entry)
        del self._audit_log[:-_MAX_AUDIT_ENTRIES]

    def get_audit_entries(self) -> list[dict]:
        """Recent pairing audit entries (newest last)."""
        return list(self._audit_log)

    # ── Query API ──

    @property
    def paired_devices(self) -> list[PairedDevice]:
        return list(self._paired_devices.values())

    def is_paired(self, device_id: str) -> bool:
        return device_id in self._paired_devices

    def is_trusted(self, device_id: str) -> bool:
        d = self._paired_devices.get(device_id)
        return d is not None and d.trusted and not d.revoked

    # ── Network policy ──

    def _ip_allowed(self, client_ip: str) -> bool:
        """Pairing policy: loopback always; LAN needs allow_lan_pairing."""
        if not client_ip:
            return True
        try:
            addr = ipaddress.ip_address(client_ip.split("%")[0])
        except ValueError:
            return False
        if addr.is_loopback:
            return True
        if not self._allow_lan_pairing:
            return False
        if self._allowed_networks:
            return any(
                addr in ipaddress.ip_network(cidr)
                for cidr in self._allowed_networks
            )
        return True

    # ── Pairing sessions ──

    def start_pairing(self) -> dict:
        session_id = secrets.token_hex(16)
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        nonce = secrets.token_hex(32)
        now = time.time()
        session = PairingSession(
            session_id=session_id,
            code=code,
            challenge=nonce,
            nonce=nonce,
            created_at=now,
            expires_at=now + self._pairing_timeout,
        )
        self._active_sessions[session_id] = session

        qr_data = (f"michi://pair?v={QR_PAYLOAD_VERSION}"
                   f"&session={session_id}&code={code}")
        qr_data_uri, mime = self._generate_qr(qr_data)
        return {"ok": True, "session_id": session_id, "code": code,
                "nonce": nonce,
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
        """Issue the proof-of-possession challenge (nonce) for a session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "SESSION_NOT_FOUND"}
        if time.time() > session.expires_at:
            self._active_sessions.pop(session_id, None)
            return {"ok": False, "error": "SESSION_EXPIRED"}
        return {"ok": True, "challenge": session.challenge,
                "nonce": session.nonce, "session_id": session_id}

    def _check_rate_limit(self, key: str) -> bool:
        now = time.time()
        attempts = [t for t in self._attempt_log.get(key, [])
                    if now - t < _RATE_WINDOW_SECONDS]
        self._attempt_log[key] = attempts
        return len(attempts) < _MAX_VERIFY_ATTEMPTS

    def _record_attempt(self, key: str) -> None:
        self._attempt_log.setdefault(key, []).append(time.time())

    def _session_state(self, session_id: str) -> tuple[PairingSession | None, str]:
        """Resolve a session; returns (session, error_code)."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None, "SESSION_NOT_FOUND"
        if time.time() > session.expires_at:
            self._active_sessions.pop(session_id, None)
            return None, "SESSION_EXPIRED"
        return session, ""

    # ── Signature challenge-response pairing ──

    def pair_request(self, session_id: str, nonce: str, public_key: str,
                     signature: str, device_id: str, name: str = "",
                     fingerprint: str = "", protocol_version: str = "1.0",
                     ip: str = "") -> dict:
        """Complete a pairing session with a real signature proof.

        The device signs ``protocol_version|session_id|nonce|fingerprint|
        device_id`` with its private key; the fingerprint is derived
        server-side from the presented public key. Success creates the
        device as ``awaiting_approval`` — it becomes trusted only after
        ``approve_device()`` (user approval).
        """
        if not self._signature_pairing_enabled:
            return {"ok": False, "error": "SIGNATURE_DISABLED"}
        session, error = self._session_state(session_id)
        if session is None:
            return {"ok": False, "error": error}
        rate_key = ip or device_id or session_id
        if not self._check_rate_limit(rate_key):
            return {"ok": False, "error": "RATE_LIMITED"}
        if not self._ip_allowed(ip):
            return {"ok": False, "error": "NETWORK_DENIED"}
        if session.nonce_used:
            return {"ok": False, "error": "NONCE_REUSED"}
        if nonce != session.nonce:
            return {"ok": False, "error": "NONCE_INVALID"}
        session.nonce_used = True
        if not signature:
            self._record_attempt(rate_key)
            return {"ok": False, "error": "SIGNATURE_REQUIRED"}
        raw_key = _parse_ed25519_public_key(public_key)
        if raw_key is None:
            self._record_attempt(rate_key)
            return {"ok": False, "error": "KEY_INVALID"}
        derived = _derive_fingerprint(raw_key)
        if fingerprint and fingerprint != derived:
            self._record_attempt(rate_key)
            return {"ok": False, "error": "FINGERPRINT_MISMATCH"}
        payload = _signature_payload(
            protocol_version, session_id, nonce, derived, device_id)
        if not _verify_ed25519_signature(raw_key, payload, signature):
            self._record_attempt(rate_key)
            return {"ok": False, "error": "SIGNATURE_INVALID"}

        existing = self._existing_trusted_device(device_id, public_key)
        if existing is not None:
            session.verified = True
            self._active_sessions.pop(session_id, None)
            self._record_audit("signature_pairing", device_id=device_id,
                               ip=ip)
            return {"ok": True, "device_id": device_id,
                    "device_name": existing.name,
                    "fingerprint": existing.fingerprint,
                    "status": "trusted"}

        device = self._create_pending_device(
            device_id=device_id, name=name, public_key=public_key,
            fingerprint=derived, protocol_version=protocol_version)
        if isinstance(device, _DeviceIdConflict):
            return {"ok": False, "error": "DEVICE_ID_CONFLICT",
                    "status": "DEVICE_ID_CONFLICT"}
        if device is None:
            return {"ok": False, "error": "PERSISTENCE_FAILED",
                    "status": "PERSISTENCE_FAILED"}
        session.verified = True
        self._record_audit("signature_pairing", device_id=device_id,
                           ip=ip)
        return {"ok": True, "device_id": device.device_id,
                "device_name": device.name, "fingerprint": device.fingerprint,
                "status": "awaiting_approval"}

    def _existing_trusted_device(self, device_id: str,
                                 public_key: str) -> PairedDevice | None:
        """Return the device when it is already trusted with the SAME key.

        Re-pairing with the same public key keeps the existing trust; any
        other key (or a revoked device) requires a new approval.
        """
        existing = self._paired_devices.get(device_id)
        if (existing is not None and existing.trusted
                and not existing.revoked
                and existing.public_key == public_key):
            return existing
        return None

    def _create_pending_device(self, device_id: str, name: str,
                               public_key: str, fingerprint: str,
                               protocol_version: str) -> PairedDevice | None:
        """Create (persist-first) a device awaiting approval.

        Never returns a device that failed to persist: on DB failure the
        device is NOT added to the trusted in-memory cache.

        Key-swap guard: if a pending device with the SAME device_id already
        exists with a DIFFERENT public key, the pairing is rejected with
        DEVICE_ID_CONFLICT — the attacker must not be able to claim a
        victim's pending device id with their own key (INSERT OR REPLACE
        would silently overwrite it).
        """
        existing = self._paired_devices.get(device_id)
        if (existing is not None and not existing.trusted
                and existing.public_key and public_key
                and existing.public_key != public_key):
            return _DeviceIdConflict()
        now = time.time()
        device = PairedDevice(
            device_id=device_id,
            name=name or "Mobile Device",
            public_key=public_key,
            fingerprint=fingerprint,
            paired_at=now,
            last_seen=now,
            trusted=False,
            protocol_version=protocol_version or QR_PAYLOAD_VERSION,
        )
        if not self._persist_device(device):
            return None
        self._paired_devices[device.device_id] = device
        return device

    # ── Legacy code-only pairing ──

    def verify_pairing(self, session_id: str, code: str, device_name: str = "",
                       device_id: str = "", public_key: str = "",
                       fingerprint: str = "", ip: str = "",
                       signature: str = "", protocol_version: str = "1.0") -> dict:
        """Complete a pairing session (code entry; optional signature).

        Signature path: the device proves possession of its private key over
        ``protocol_version|session_id|nonce|fingerprint|device_id``; the
        fingerprint is derived server-side. Code-only path is accepted ONLY
        when ``legacy_code_pairing_enabled`` is set; it never auto-trusts
        (device is created ``awaiting_approval``) and is audit-flagged as
        insecure legacy pairing.
        """
        session, error = self._session_state(session_id)
        if session is None:
            return {"ok": False, "error": error}
        rate_key = ip or device_id or session_id
        if not self._check_rate_limit(rate_key):
            return {"ok": False, "error": "RATE_LIMITED"}
        if not self._ip_allowed(ip):
            return {"ok": False, "error": "NETWORK_DENIED"}
        if session.code != code:
            self._record_attempt(rate_key)
            return {"ok": False, "error": "INVALID_CODE"}

        if public_key or signature:
            if not signature:
                self._record_attempt(rate_key)
                return {"ok": False, "error": "SIGNATURE_REQUIRED"}
            if not self._signature_pairing_enabled:
                return {"ok": False, "error": "SIGNATURE_DISABLED"}
            raw_key = _parse_ed25519_public_key(public_key)
            if raw_key is None:
                self._record_attempt(rate_key)
                return {"ok": False, "error": "KEY_INVALID"}
            derived = _derive_fingerprint(raw_key)
            if fingerprint and fingerprint != derived:
                self._record_attempt(rate_key)
                return {"ok": False, "error": "FINGERPRINT_MISMATCH"}
            payload = _signature_payload(
                protocol_version, session_id, session.nonce, derived,
                device_id)
            if not _verify_ed25519_signature(raw_key, payload, signature):
                self._record_attempt(rate_key)
                return {"ok": False, "error": "SIGNATURE_INVALID"}
            session.nonce_used = True
            existing = self._existing_trusted_device(device_id, public_key)
            if existing is not None:
                session.verified = True
                self._active_sessions.pop(session_id, None)
                self._record_audit("signature_pairing", device_id=device_id,
                                   ip=ip)
                return {"ok": True, "device_id": device_id,
                        "device_name": existing.name,
                        "fingerprint": existing.fingerprint,
                        "status": "trusted"}
            device = self._create_pending_device(
                device_id=device_id, name=device_name,
                public_key=public_key, fingerprint=derived,
                protocol_version=protocol_version)
            if device is None:
                return {"ok": False, "error": "PERSISTENCE_FAILED",
                        "status": "PERSISTENCE_FAILED"}
            session.verified = True
            self._active_sessions.pop(session_id, None)
            self._record_audit("signature_pairing", device_id=device_id,
                               ip=ip)
            return {"ok": True, "device_id": device.device_id,
                    "device_name": device.name,
                    "fingerprint": device.fingerprint,
                    "status": "awaiting_approval"}

        # ── Code-only (legacy) path ──
        if not self._legacy_code_pairing_enabled:
            return {"ok": False, "error": "SIGNATURE_REQUIRED"}
        did = device_id or hashlib.sha256(
            f"{session_id}:{device_name}".encode()
        ).hexdigest()[:16]
        device = self._create_pending_device(
            device_id=did, name=device_name, public_key="",
            fingerprint="", protocol_version=protocol_version)
        if isinstance(device, _DeviceIdConflict):
            return {"ok": False, "error": "DEVICE_ID_CONFLICT",
                    "status": "DEVICE_ID_CONFLICT"}
        if device is None:
            return {"ok": False, "error": "PERSISTENCE_FAILED",
                    "status": "PERSISTENCE_FAILED"}
        session.verified = True
        self._active_sessions.pop(session_id, None)
        self._record_audit("legacy_code_pairing", device_id=did, ip=ip)
        return {"ok": True, "device_id": did, "device_name": device.name,
                "status": "awaiting_approval"}

    # ── Trust lifecycle ──

    def approve_device(self, device_id: str) -> dict:
        """User approval: persists the device as trusted (never memory-only)."""
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        updated = PairedDevice(**d.__dict__)
        updated.trusted = True
        updated.revoked = False
        if not self._persist_device(updated):
            return {"ok": False, "error": "PERSISTENCE_FAILED",
                    "status": "PERSISTENCE_FAILED"}
        self._paired_devices[device_id] = updated
        self._record_audit("device_approved", device_id=device_id)
        return {"ok": True}

    def unpair(self, device_id: str) -> dict:
        device = self._paired_devices.get(device_id)
        if device is None:
            return {"ok": False, "error": "NOT_FOUND"}
        self._paired_devices.pop(device_id, None)
        self._delete_device(device_id)
        return {"ok": True}

    def trust_device(self, device_id: str) -> dict:
        return self.approve_device(device_id)

    def revoke_trust(self, device_id: str) -> dict:
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        updated = PairedDevice(**d.__dict__)
        updated.trusted = False
        updated.revoked = True
        if not self._persist_device(updated):
            return {"ok": False, "error": "PERSISTENCE_FAILED",
                    "status": "PERSISTENCE_FAILED"}
        self._paired_devices[device_id] = updated
        self._record_audit("device_revoked", device_id=device_id)
        return {"ok": True}

    def get_pairing_info(self, device_id: str) -> dict | None:
        d = self._paired_devices.get(device_id)
        if not d:
            return None
        return {"device_id": d.device_id, "name": d.name,
                "public_key": d.public_key, "fingerprint": d.fingerprint,
                "paired_at": d.paired_at, "last_seen": d.last_seen,
                "trusted": d.trusted, "revoked": d.revoked,
                "protocol_version": d.protocol_version,
                "status": "revoked" if d.revoked else (
                    "trusted" if d.trusted else "awaiting_approval")}

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
                               "has_challenge": bool(s.challenge),
                               "has_nonce": bool(s.nonce),
                               "nonce_used": s.nonce_used})
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
        listener = _Listener(
            db=self._db, port=self._server_port,
            registry=self._device_registry, pairing_service=self,
            bind_host=self._bind_host,
            import_store_path=self._import_store_path,
        )
        ok, error = listener.start()
        if not ok:
            self._last_error = error or "LISTENER_START_FAILED"
            self._routes_mounted = False
            if error == "ROUTES_NOT_MOUNTED":
                return {"ok": False, "error": "ROUTES_NOT_MOUNTED",
                        "listening": False}
            return {"ok": False, "error": "LISTENER_START_FAILED",
                    "detail": self._last_error}
        self._listener = listener
        self._routes_mounted = listener.routes_mounted
        self._last_error = ""
        return {"ok": True, "port": listener.port, "listening": True}

    def stop(self) -> dict:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._routes_mounted = False
        return {"ok": True}

    def shutdown(self) -> None:
        """Container shutdown hook (stops the listener)."""
        self.stop()

    def is_listening(self) -> bool:
        """Truthful live probe: True only when a socket answers on our port."""
        if self._listener is None or not self._listener.is_running:
            return False
        port = self._listener.port
        probe_host = self._listener.bind_host
        if probe_host in ("0.0.0.0", "", "::"):
            probe_host = "127.0.0.1"
        try:
            with socket.create_connection((probe_host, port), timeout=0.5):
                return True
        except OSError:
            return False

    # ── Health ──

    def health(self) -> dict:
        loopback_bind = self._bind_host in ("127.0.0.1", "localhost", "::1") \
            or self._bind_host.startswith("127.")
        bind_allowed = loopback_bind or self._allow_lan_pairing
        return {
            "protocol_supported": QR_PAYLOAD_VERSION,
            "server_configured": True,
            "server_listening": self.is_listening(),
            "tls_available": self._tls_mode != "none",
            "tls_mode": self._tls_mode,
            "secure_pairing_available": (
                self._signature_pairing_enabled and bind_allowed),
            "signature_pairing_enabled": self._signature_pairing_enabled,
            "insecure_legacy_enabled": self._legacy_code_pairing_enabled,
            "legacy_ttl_seconds": self._legacy_ttl,
            "bind_host": self._bind_host,
            "allow_lan_pairing": self._allow_lan_pairing,
            "allowed_networks": list(self._allowed_networks),
            "routes_mounted": self._routes_mounted,
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
            "audit_entries": len(self._audit_log),
        }
