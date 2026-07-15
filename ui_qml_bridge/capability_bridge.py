"""CapabilityBridge — exposes backend capabilities to QML.

Based on BridgeFactory._capabilities + real service availability.
No inline SQL — delegates to service capability checks.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property


CAPABILITY_STATE_KEYS = {
    "library", "playback", "nowplaying", "mix", "lyrics",
    "connections_michilink", "home_audio", "snapcast",
    "devices_sync", "radio", "playlists", "eq",
    "settings", "audio_lab", "metadata", "smart_tagging",
    "disc_lab", "library_doctor", "diagnostics",
    "michi_ai", "theme", "navigation", "route_registry",
    "app_state", "command_palette", "cover",
    "notifications", "global_search",
}


class CapabilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, factory=None, parent=None):
        super().__init__(parent)
        self._factory = factory
        self._caps: dict[str, str] = {}

    def refresh(self):
        if not self._factory:
            return
        caps = dict(self._factory.capabilities)
        svc = self._factory._services if hasattr(self._factory, '_services') else None
        for key in CAPABILITY_STATE_KEYS:
            if key not in caps:
                caps[key] = "unavailable"
        caps["has_fts5"] = "available" if self._check_fts5(svc) else "unavailable"
        caps["has_radio"] = "available" if (svc and svc.has("radio_manager")) else "unavailable"
        caps["has_sync"] = "available" if (svc and svc.has("sync_manager")) else "unavailable"
        caps["has_home_audio"] = "available" if (svc and svc.has("home_audio_controller")) else "unavailable"
        caps["has_snapcast"] = "available" if (svc and svc.has("snapcast_controller")) else "unavailable"
        caps["has_disc_service"] = "available" if (svc and svc.has("disc_service")) else "unavailable"
        caps["has_smart_tagging"] = "available" if (svc and svc.has("smart_tagging_service")) else "unavailable"
        caps["has_metadata_writer"] = "available" if self._check_metadata_writer(svc) else "unavailable"
        self._caps = caps
        self.dataChanged.emit()

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    def has(self, name: str) -> bool:
        val = self._caps.get(name, "unavailable")
        if val == "available":
            return True
        return val == "available"

    def _check_fts5(self, svc) -> bool:
        return bool(svc and svc.search_engine)

    def _check_metadata_writer(self, svc) -> bool:
        import importlib.util
        return importlib.util.find_spec("mutagen") is not None
