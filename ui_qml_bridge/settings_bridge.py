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
            {"id": "output", "title": "Salida", "desc": "Perfiles de salida, dispositivo, backend"},
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
                    "key": p.key, "name": p.name, "description": p.description,
                    "allows_eq": p.allows_eq, "allows_replaygain": p.allows_replaygain,
                    "bitperfect": p.bitperfect, "preferred_backend": p.preferred_backend,
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

    @Slot(str, result=dict)
    def setActiveProfile(self, key: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set("audio/profile", key)
            self.settingsChanged.emit()
            return {"ok": True}
        except Exception as e:
            logger.debug("Failed to set profile %s", key, exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(str, result=str)
    def get(self, key: str):
        try:
            from core.settings_manager import get as settings_get
            return str(settings_get(key) or "")
        except Exception:
            return ""

    @Slot(str, str, result=dict)
    def set(self, key: str, value: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set(key, value)
            self.settingsChanged.emit()
            return {"ok": True}
        except Exception as e:
            logger.debug("Settings set failed for %s", key, exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def getDSPState(self):
        try:
            from core.settings_manager import get as settings_get
            return {
                "ok": True,
                "crossfade": settings_get("playback/crossfade") or 0,
                "replaygain": settings_get("audio/replaygain") or "disabled",
                "eq_enabled": settings_get("audio/eq_enabled") or False,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def setDSP(self, key: str, value: str):
        try:
            from core.settings_manager import set_ as settings_set
            settings_set(f"audio/{key}", value)
            self.settingsChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
