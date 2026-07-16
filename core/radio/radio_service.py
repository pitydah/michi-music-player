"""RadioService — thin adapter to radio manager logic."""
from __future__ import annotations

import logging

logger = logging.getLogger("core.radio.radio_service")


class RadioService:
    def __init__(self, radio_manager=None, db=None):
        self._radio_manager = radio_manager
        self._db = db
        self._buffer_ms = 2000
        self._timeout_s = 10
        self._reconnect_policy = "automatic"

    @property
    def radio_manager(self):
        return self._radio_manager

    def get_stations(self, filter_text: str = "") -> list:
        if self._radio_manager:
            return self._radio_manager.get_stations(filter_text)
        return []

    def play_station(self, url: str, name: str) -> bool:
        if self._radio_manager:
            return self._radio_manager.play(url, name)
        return False

    def stop(self) -> dict:
        if self._radio_manager and hasattr(self._radio_manager, 'stop'):
            try:
                self._radio_manager.stop()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def get_buffer_ms(self) -> int:
        return self._buffer_ms

    def set_buffer_ms(self, ms: int):
        self._buffer_ms = max(500, min(30000, ms))

    def get_timeout_s(self) -> int:
        return self._timeout_s

    def set_timeout_s(self, s: int):
        self._timeout_s = max(3, min(120, s))

    def get_reconnect_policy(self) -> str:
        return self._reconnect_policy

    def set_reconnect_policy(self, policy: str):
        if policy in ("automatic", "manual", "disabled"):
            self._reconnect_policy = policy
