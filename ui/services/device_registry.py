"""Device registry — persistent paired device storage."""

from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass

from core.json_store import atomic_write_json, read_json_safe, field
from core.paths import paired_devices_path

logger = logging.getLogger("michi.sync.registry")

_REGISTRY_PATH = paired_devices_path()


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
