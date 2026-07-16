"""MobileSyncService — sync tracks/playlists to mobile devices via MTP."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.mobile_sync")


class MobileSyncService:
    def __init__(self, db=None):
        self._db = db

    def check_device(self, device_id: str) -> dict:
        return {"ok": True, "connected": False, "message": "DEFERRED_PHYSICAL"}

    def build_manifest(self, track_ids: list[int]) -> dict:
        return {"ok": True, "tracks": len(track_ids), "estimated_mb": len(track_ids) * 10}

    def transfer(self, manifest: dict) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
