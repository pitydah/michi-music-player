"""Device registry — persistent paired device storage."""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field

from core.json_store import atomic_write_json, read_json_safe

logger = logging.getLogger("michi.sync.registry")

_REGISTRY_PATH = os.path.expanduser("~/.local/share/michi-music-player/paired_devices.json")


@dataclass
class PairedDevice:
    device_id: str = ""
    name: str = ""
    device_type: str = "android"
    host: str = ""
    port: int = 53318
    status: str = "disconnected"
    last_seen: str = ""
    last_sync: str = ""
    last_manifest_ts: str = ""
    preferred_profile: str = "original"
    paired_at: str = ""
    device_model: str = ""
    client_version: str = ""
    last_ip: str = ""
    capabilities: list = field(default_factory=list)
    trusted: bool = False
    token_hash: str = ""
    permissions: list = field(default_factory=lambda: [
        "sync.read_manifest", "sync.download_tracks",
        "sync.download_covers", "sync.download_playlists", "sync.upload_state",
    ])
    allowed_playlists: list = field(default_factory=list)
    sync_mode: str = "selected_playlists"
    revoked_at: str = ""
    last_pairing_at: str = ""


class DeviceRegistry:
    def __init__(self, path: str = _REGISTRY_PATH):
        self._path = path
        self._devices: dict[str, PairedDevice] = {}
        self._load()

    def _load(self):
        data = read_json_safe(self._path, default=[], backup_corrupt=True)
        if not isinstance(data, list):
            return
        for item in data:
            with contextlib.suppress(Exception):
                d = PairedDevice(**item)
                self._devices[d.device_id] = d

    def _save(self):
        data = [d.__dict__ for d in self._devices.values()]
        atomic_write_json(self._path, data)

    def register(self, device_id: str, name: str, host: str = "",
                 port: int = 53318, device_type: str = "android",
                 device_model: str = "", client_version: str = "") -> bool:
        if device_id in self._devices:
            return False
        d = PairedDevice(
            device_id=device_id, name=name, device_type=device_type,
            host=host, port=port,
            device_model=device_model, client_version=client_version,
            paired_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self._devices[device_id] = d
        self._save()
        return True

    def update(self, device_id: str, **kwargs):
        d = self._devices.get(device_id)
        if d:
            for k, v in kwargs.items():
                if hasattr(d, k):
                    setattr(d, k, v)
            self._save()

    def remove(self, device_id: str):
        if device_id in self._devices:
            del self._devices[device_id]
            self._save()

    def get(self, device_id: str) -> PairedDevice | None:
        return self._devices.get(device_id)

    def list_all(self) -> list[PairedDevice]:
        return list(self._devices.values())

    def mark_seen(self, device_id: str, name: str = "", host: str = ""):
        d = self._devices.get(device_id)
        if d:
            d.last_seen = time.strftime("%Y-%m-%dT%H:%M:%S")
            if name:
                d.name = name
            if host:
                d.host = host
            self._save()

    def set_token(self, device_id: str, token: str):
        d = self._devices.get(device_id)
        if d:
            d.token_hash = hashlib.sha256(token.encode()).hexdigest()
            d.last_pairing_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            d.trusted = True
            d.revoked_at = ""
            self._save()

    def validate_token(self, device_id: str, token: str) -> bool:
        d = self._devices.get(device_id)
        if not d or not d.token_hash or d.revoked_at:
            return False
        calculated = hashlib.sha256(token.encode()).hexdigest()
        return secrets.compare_digest(calculated, d.token_hash)

    def revoke(self, device_id: str):
        d = self._devices.get(device_id)
        if d:
            d.trusted = False
            d.revoked_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._save()

    def has_permission(self, device_id: str, permission: str) -> bool:
        d = self._devices.get(device_id)
        if not d or d.revoked_at:
            return False
        return permission in d.permissions

    def update_permissions(self, device_id: str, permissions: list[str]):
        d = self._devices.get(device_id)
        if d:
            d.permissions = permissions
            self._save()
