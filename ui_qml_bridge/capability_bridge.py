"""CapabilityBridge — exposes backend capabilities to QML.

Based on BridgeFactory._capabilities + ServiceContainer availability.
No inline SQL — delegates to service capability checks.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


CAPABILITY_LABELS = {
    "connections_michilink": "Michi Link",
    "home_audio": "Home Audio",
    "snapcast": "Snapcast",
    "devices_sync": "Sincronización de dispositivos",
    "radio": "Radio",
    "playlists": "Playlists",
    "eq": "Ecualizador",
    "settings": "Ajustes",
    "audio_lab": "Audio Lab",
    "metadata": "Editor de metadatos",
    "smart_tagging": "Smart Tagging",
    "disc_lab": "Disc Lab",
    "library_doctor": "Library Doctor",
    "diagnostics": "Diagnóstico",
    "michi_ai": "Michi AI",
    "library": "Biblioteca",
    "playback": "Reproducción",
    "mix": "Mix",
    "lyrics": "Letras",
    "notifications": "Notificaciones",
    "global_search": "Búsqueda global",
    "transmit": "Transmitir audio",
    "ai": "Michi AI",
    "connections": "Conexiones",
    "devices": "Dispositivos",
    "output_profiles": "Perfiles de salida",
}

BRIDGE_ALIASES = {
    "transmit": "home_audio",
    "ai": "michi_ai",
}


def _resolve_alias(name: str) -> str:
    return BRIDGE_ALIASES.get(name, name)


CAPABILITY_STATE_KEYS = {
    "library", "playback", "nowplaying", "mix", "lyrics",
    "connections_michilink", "home_audio", "snapcast",
    "devices_sync", "radio", "playlists", "eq",
    "settings", "audio_lab", "metadata", "smart_tagging",
    "disc_lab", "library_doctor", "diagnostics",
    "michi_ai", "theme", "navigation", "route_registry",
    "app_state", "command_palette", "cover",
    "notifications", "global_search",
    "connections", "devices", "output_profiles",
    "ai", "transmit",
}


class CapabilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, factory=None, parent=None):
        super().__init__(parent)
        logger.debug("CapabilityBridge.__init__ called")
        self._factory = factory
        self._caps: dict[str, str] = {}

    @Slot(result="QVariantMap")
    def refresh(self):
        if not self._factory:
            return {"ok": False, "error": "NO_FACTORY"}
        caps = dict(self._factory.capabilities)
        container = getattr(self._factory, '_container', None)
        for key in CAPABILITY_STATE_KEYS:
            if key not in caps:
                resolved = _resolve_alias(key)
                if resolved != key and resolved in caps:
                    caps[key] = caps[resolved]
                else:
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
        self._wire_navigation()
        self.dataChanged.emit()
        return {"ok": True, "capabilities": dict(self._caps)}

    def _wire_navigation(self):
        if not self._factory:
            return
        nav = self._factory.get("navigation")
        if nav is None or not hasattr(nav, 'set_capabilities'):
            return
        available = {key for key, val in self._caps.items() if val == "available"}
        try:
            nav.set_capabilities(available)
        except Exception:
            logger.debug("Failed to wire navigation capabilities", exc_info=True)

    @Property("QVariantMap", notify=dataChanged)
    def capabilities(self):
        return dict(self._caps)

    @Slot(str, result=bool)
    def has(self, name: str) -> bool:
        val = self._caps.get(name, "unavailable")
        return val == "available"

    @Slot(str, result=str)
    def label(self, name: str) -> str:
        return CAPABILITY_LABELS.get(_resolve_alias(name), name)

    @Slot(str, result=str)
    def state(self, name: str) -> str:
        if name in self._caps:
            return self._caps[name]
        resolved = _resolve_alias(name)
        if resolved != name and resolved in self._caps:
            return self._caps[resolved]
        return "unavailable"

    def _check_fts5(self, container) -> bool:
        return bool(container and container.contains("global_search_service"))

    def _check_metadata_writer(self, container) -> bool:
        import importlib.util
        return importlib.util.find_spec("mutagen") is not None
