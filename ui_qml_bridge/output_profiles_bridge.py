"""OutputProfilesBridge — QML bridge for audio output profiles."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class OutputProfilesBridge(QObject):
    dataChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._profiles: list[dict] = []
        self._active_id = ""

    @Property("QVariantList", notify=dataChanged)
    def profiles(self):
        return list(self._profiles)

    @Property(str, notify=dataChanged)
    def activeProfileId(self):
        return self._active_id

    @Slot(result=dict)
    def refresh(self):
        if not self._player:
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            from audio.output_profiles import PROFILES
            self._profiles = [
                {"id": k, "name": v.get("name", k),
                 "backend": v.get("preferred_backend", "gstreamer"),
                 "allows_eq": v.get("allows_eq", False),
                 "bitperfect": v.get("bitperfect", False),
                 "dsd_mode": v.get("dsd_mode", "pcm")}
                for k, v in PROFILES.items()
            ]
            if hasattr(self._player, 'get_active_profile_id'):
                self._active_id = self._player.get_active_profile_id() or ""
            self.dataChanged.emit()
            return {"ok": True, "count": len(self._profiles)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def setActiveProfile(self, profile_id: str):
        if not self._player or not hasattr(self._player, 'set_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.set_profile(profile_id)
            self._active_id = profile_id
            self.dataChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
