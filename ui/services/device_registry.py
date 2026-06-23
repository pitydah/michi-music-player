"""Device registry — persistent paired device storage."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass

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
    preferred_profile: str = "original"
    paired_at: str = ""


class DeviceRegistry:
    def __init__(self, path: str = _REGISTRY_PATH):
        self._path = path
        self._devices: dict[str, PairedDevice] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    data = json.load(f)
                for item in data:
                    d = PairedDevice(**item)
                    self._devices[d.device_id] = d
            except Exception as e:
                logger.warning("Device registry load failed: %s", e)

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = [d.__dict__ for d in self._devices.values()]
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def register(self, device_id: str, name: str, host: str = "",
                 port: int = 53318, device_type: str = "android") -> bool:
        if device_id in self._devices:
            return False
        d = PairedDevice(
            device_id=device_id, name=name, device_type=device_type,
            host=host, port=port,
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
