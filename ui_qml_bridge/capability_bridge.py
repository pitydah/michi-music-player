"""CapabilityBridge — exposes backend capabilities to QML.

Based on BridgeFactory._capabilities + ServiceContainer availability.
No inline SQL — delegates to service capability checks.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


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
        logger.debug("CapabilityBridge.__init__ called")
        self._factory = factory
        self._caps: dict[str, str] = {}

    def refresh(self):
        if not self._factory:
            return
        caps = dict(self._factory.capabilities)
        container = getattr(self._factory, '_container', None)
        for key in CAPABILITY_STATE_KEYS:
            if key not in caps:
                caps[key] = "unavailable"
        caps["has_fts5"] = "available" if self._check_fts5(container) else "unavailable"
        caps["has_radio"] = "available" if (container and container.contains("radio_service")) else "unavailable"
        caps["has_sync"] = "available" if (container and container.contains("device_sync_service")) else "unavailable"
        caps["has_home_audio"] = "available" if (container and container.contains("home_audio_service")) else "unavailable"
        caps["has_snapcast"] = "available" if (container and container.contains("home_audio_service")) else "unavailable"
        caps["has_disc_service"] = "available" if (container and container.contains("library_doctor_service")) else "unavailable"
        caps["has_smart_tagging"] = "available" if (container and container.contains("smart_tagging_service")) else "unavailable"
        caps["has_metadata_writer"] = "available" if self._check_metadata_writer(container) else "unavailable"
        self._caps = caps
        self.dataChanged.emit()

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    @Slot(str, result=bool)
    def has(self, name: str) -> bool:
        val = self._caps.get(name, "unavailable")
        return val == "available"

    def _check_fts5(self, container) -> bool:
        return bool(container and container.contains("global_search_service"))

    def _check_metadata_writer(self, container) -> bool:
        import importlib.util
        return importlib.util.find_spec("mutagen") is not None
