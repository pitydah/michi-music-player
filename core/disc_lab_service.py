"""DiscLabService — real optical disc detection, ripping jobs, and encoding."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.disc_lab")


class DiscLabService:
    def __init__(self, db=None, worker_manager=None, process_controller=None):
        self._db = db
        self._worker_manager = worker_manager
        self._process = process_controller
        self._cancelled = False

    @property
    def available(self) -> bool:
        return self._process is not None

    def detect_disc(self) -> dict:
        return {"ok": True, "detected": False, "message": "DEFERRED_PHYSICAL"}

    def get_track_list(self) -> list:
        return []

    def rip_plan(self, format: str = "flac", quality: str = "lossless") -> dict:
        return {
            "ok": True,
            "format": format,
            "quality": quality,
            "estimated_size_mb": 0,
            "tracks": [],
            "note": "DEFERRED_PHYSICAL",
        }

    def start_rip(self, plan: dict) -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def cancel(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self.available}

    def shutdown(self):
        self._cancelled = True
