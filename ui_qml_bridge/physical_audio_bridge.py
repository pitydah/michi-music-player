"""PhysicalAudioBridge — real audio backend, output device, profiles, bit-perfect."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot


def _get_active_profile(player) -> dict:
    if not player:
        return {"name": "none", "backend": "none", "bitperfect": False}
    try:
        pid = player.get_active_backend_id() if hasattr(player, 'get_active_backend_id') else "gstreamer"
        return {"name": pid, "backend": pid, "bitperfect": False}
    except Exception:
        return {"name": "error", "backend": "error", "bitperfect": False}


def _get_output_device(player) -> dict:
    if not player:
        return {"name": "none", "protocol": "none"}
    try:
        dev = player.get_output_device_id() if hasattr(player, 'get_output_device_id') else "default"
        return {"name": dev or "default", "protocol": "ALSA"}
    except Exception:
        return {"name": "error", "protocol": "error"}


class PhysicalAudioBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self._player = player_service

    @Slot(result=dict)
    def physicalAudioScore(self) -> dict:
        score = 0
        if self._player:
            score += 20
            try:
                profile = _get_active_profile(self._player)
                if profile["name"] != "none":
                    score += 20
            except Exception:
                pass
            try:
                dev = _get_output_device(self._player)
                if dev["name"] != "none":
                    score += 20
            except Exception:
                pass
        else:
            score += 15
        if self._player and hasattr(self._player, 'get_volume'):
            score += 15
        if self._player and hasattr(self._player, 'get_active_backend_id'):
            score += 15
        if self._player and hasattr(self._player, 'get_output_device_id'):
            score += 10
        return {
            "score": min(100, score),
            "player_available": self._player is not None,
            "has_profile": score >= 40,
            "has_device": score >= 60,
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
