"""SettingsBridge — connects QML Settings page to real SettingsManager."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.settings")


class SettingsBridge(QObject):
    settingsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections = []

    @Slot()
    def refresh(self):
        self.settingsChanged.emit()

    @Property("QVariantList", notify=settingsChanged)
    def sections(self):
        return [
            {"id": "general", "title": "General", "desc": "Idioma, comportamiento, ventana"},
            {"id": "appearance", "title": "Apariencia", "desc": "Tema, colores, tipografía"},
            {"id": "library", "title": "Biblioteca", "desc": "Carpetas, escaneo, organización"},
            {"id": "playback", "title": "Reproducción", "desc": "Salida de audio, volumen, crossfade"},
            {"id": "audio", "title": "Audio avanzado", "desc": "Hybrid Engine, MPD, DSP, EQ"},
            {"id": "michi_link", "title": "Michi Link", "desc": "Micro Server, Sync, red"},
            {"id": "privacy", "title": "Privacidad", "desc": "Recognition, datos, red local"},
            {"id": "experimental", "title": "Experimental", "desc": "Funciones en desarrollo"},
        ]

    @Property("QVariantList", notify=settingsChanged)
    def outputProfiles(self):
        try:
            from audio.output_profiles import PROFILES
            return [
                {
                    "key": p.key,
                    "name": p.name,
                    "description": p.description,
                    "allows_eq": p.allows_eq,
                    "allows_replaygain": p.allows_replaygain,
                    "bitperfect": p.bitperfect,
                    "preferred_backend": p.preferred_backend,
                }
                for p in PROFILES.values()
            ]
        except Exception:
            logger.debug("Failed to load output profiles", exc_info=True)
            return []

    @Slot(str, result=str)
    def getActiveProfile(self):
        try:
            from core.settings_manager import get as settings_get
            return settings_get("audio/profile") or "standard"
        except Exception:
            return "standard"

    @Slot(str)
    def setActiveProfile(self, key: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("audio/profile", key)
            self.settingsChanged.emit()
        except Exception:
            logger.debug("Failed to set profile %s", key, exc_info=True)

    @Slot(str, result=str)
    def get(self, key: str):
        try:
            from core.settings_manager import get as settings_get
            return str(settings_get(key) or "")
        except Exception:
            logger.debug("Settings get failed for %s", key, exc_info=True)
            return ""

    @Slot(str, str)
    def set(self, key: str, value: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set(key, value)
            self.settingsChanged.emit()
        except Exception:
            logger.debug("Settings set failed for %s", key, exc_info=True)
