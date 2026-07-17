"""CapabilityBridge — exposes productive feature availability to QML."""
from __future__ import annotations

import importlib.util
import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

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
        self._factory = factory
        self._caps: dict[str, str] = {}

    @Slot(result="QVariantMap")
    def refresh(self):
        if not self._factory:
            self._caps = {key: "unavailable" for key in CAPABILITY_STATE_KEYS}
            self.dataChanged.emit()
            return dict(self._caps)

        caps = dict(self._factory.capabilities)
        container = getattr(self._factory, "_container", None)
        bridge_keys = set(getattr(self._factory, "_bridges", {}).keys())

        for key in CAPABILITY_STATE_KEYS:
            if key not in caps:
                caps[key] = "available" if key in bridge_keys else "unavailable"

        caps["has_fts5"] = "available" if self._check_fts5(container) else "unavailable"
        caps["has_radio"] = "available" if self._contains(container, "radio_service") else "unavailable"
        caps["has_sync"] = "available" if self._contains(container, "device_sync_service") else "unavailable"
        caps["has_home_audio"] = "available" if self._contains(container, "home_audio_service") else "unavailable"
        caps["has_snapcast"] = "available" if self._contains(container, "home_audio_service") else "unavailable"
        caps["has_disc_service"] = "available" if self._contains(container, "library_doctor_service") else "unavailable"
        caps["has_smart_tagging"] = "available" if self._contains(container, "smart_tagging_service") else "unavailable"
        caps["has_metadata_writer"] = "available" if self._check_metadata_writer() else "unavailable"

        self._caps = caps
        self.dataChanged.emit()
        return dict(self._caps)

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    @Slot(str, result=bool)
    def has(self, name: str) -> bool:
        return self._caps.get(name, "unavailable") == "available"

    @Slot(str, result=str)
    def state(self, name: str) -> str:
        return self._caps.get(name, "unavailable")

    @staticmethod
    def _contains(container, service_name: str) -> bool:
        return bool(container and container.contains(service_name))

    def _check_fts5(self, container) -> bool:
        if not self._contains(container, "global_search_service"):
            return False
        service = container.get("global_search_service")
        checker = getattr(service, "has_fts5", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception as exc:
                logger.debug("FTS5 capability check failed: %s", exc)
                return False
        return True

    @staticmethod
    def _check_metadata_writer() -> bool:
        return importlib.util.find_spec("mutagen") is not None
