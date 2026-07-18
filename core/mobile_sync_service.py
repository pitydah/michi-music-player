"""MobileSyncService — pairing, authentication, and sync with Michi mobile client."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("michi.mobile_sync")


@dataclass
class PairedDevice:
    device_id: str
    name: str
    public_key: str = ""
    paired_at: float = 0.0
    last_seen: float = 0.0
    trusted: bool = False
    protocol_version: str = "1.0"


@dataclass
class PairingSession:
    session_id: str
    code: str
    created_at: float
    expires_at: float
    verified: bool = False
    device_id: str = ""


class MobileSyncService:
    def __init__(self, db=None, event_bus=None):
        self._db = db
        self._event_bus = event_bus
        self._paired_devices: dict[str, PairedDevice] = {}
        self._active_sessions: dict[str, PairingSession] = {}
        self._server_port = 28700
        self._pairing_timeout = 300  # 5 minutes

    @property
    def paired_devices(self) -> list[PairedDevice]:
        return list(self._paired_devices.values())

    def is_paired(self, device_id: str) -> bool:
        return device_id in self._paired_devices

    def is_trusted(self, device_id: str) -> bool:
        d = self._paired_devices.get(device_id)
        return d is not None and d.trusted

    def start_pairing(self) -> dict:
        session_id = secrets.token_hex(16)
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        now = time.time()
        session = PairingSession(
            session_id=session_id,
            code=code,
            created_at=now,
            expires_at=now + self._pairing_timeout,
        )
        self._active_sessions[session_id] = session
        return {"ok": True, "session_id": session_id, "code": code,
                "expires_at": session.expires_at}

    def verify_pairing(self, session_id: str, code: str, device_name: str = "",
                       device_id: str = "") -> dict:
        session = self._active_sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "SESSION_NOT_FOUND"}
        if time.time() > session.expires_at:
            del self._active_sessions[session_id]
            return {"ok": False, "error": "SESSION_EXPIRED"}
        if session.code != code:
            return {"ok": False, "error": "INVALID_CODE"}
        session.verified = True
        did = device_id or hashlib.sha256(f"{session_id}:{device_name}".encode()).hexdigest()[:16]
        device = PairedDevice(
            device_id=did,
            name=device_name or "Mobile Device",
            paired_at=time.time(),
            last_seen=time.time(),
            trusted=True,
        )
        self._paired_devices[did] = device
        return {"ok": True, "device_id": did, "device_name": device.name}

    def unpair(self, device_id: str) -> dict:
        if device_id in self._paired_devices:
            del self._paired_devices[device_id]
            return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def trust_device(self, device_id: str) -> dict:
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        d.trusted = True
        return {"ok": True}

    def revoke_trust(self, device_id: str) -> dict:
        d = self._paired_devices.get(device_id)
        if not d:
            return {"ok": False, "error": "NOT_FOUND"}
        d.trusted = False
        return {"ok": True}

    def get_pairing_info(self, device_id: str) -> dict | None:
        d = self._paired_devices.get(device_id)
        if not d:
            return None
        return {"device_id": d.device_id, "name": d.name,
                "paired_at": d.paired_at, "last_seen": d.last_seen,
                "trusted": d.trusted, "protocol_version": d.protocol_version}

    def get_pending_sessions(self) -> list[dict]:
        now = time.time()
        active = []
        expired = []
        for sid, s in self._active_sessions.items():
            if now > s.expires_at:
                expired.append(sid)
            else:
                active.append({"session_id": sid, "created_at": s.created_at,
                               "expires_at": s.expires_at, "verified": s.verified})
        for sid in expired:
            del self._active_sessions[sid]
        return active

    def set_port(self, port: int):
        self._server_port = max(1024, min(65535, port))

    def get_port(self) -> int:
        return self._server_port

    def health(self) -> dict:
        return {"paired": len(self._paired_devices),
                "active_sessions": len([s for s in self._active_sessions.values()
                                       if time.time() <= s.expires_at]),
                "port": self._server_port}
