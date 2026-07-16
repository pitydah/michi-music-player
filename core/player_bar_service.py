"""PlayerBarService — playback state, position, volume, quality."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.player_bar")


class PlayerBarService:
    def __init__(self, player_service=None):
        self._player = player_service

    def get_state(self) -> str:
        return getattr(self._player, 'state', 'stopped') if self._player else 'stopped'

    def get_position(self) -> float:
        if self._player and hasattr(self._player, 'position'):
            try:
                return self._player.position()
            except Exception:
                pass
        return 0.0

    def get_volume(self) -> int:
        if self._player and hasattr(self._player, 'volume'):
            try:
                return self._player.volume()
            except Exception:
                pass
        return 75

    def health(self) -> dict:
        return {"available": self._player is not None}

    def shutdown(self):
        pass
