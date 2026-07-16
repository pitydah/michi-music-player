"""MTPAdapter — MTP device adapter. DEFERRED_PHYSICAL."""
from __future__ import annotations


class MTPAdapter:
    def __init__(self):
        self._connected = False

    @property
    def available(self) -> bool:
        return False

    def connect(self, device_id: str) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def disconnect(self) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def list_storage(self) -> list:
        return []
