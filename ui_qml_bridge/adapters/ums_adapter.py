"""UMSAdapter — USB Mass Storage device adapter. DEFERRED_PHYSICAL."""
from __future__ import annotations


class UMSAdapter:
    def __init__(self):
        self._mounted = False

    @property
    def available(self) -> bool:
        return False

    def mount(self, device_path: str) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def unmount(self) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def list_files(self, path: str = "") -> list:
        return []
