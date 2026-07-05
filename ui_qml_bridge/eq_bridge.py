"""EqBridge — connects QML EQ page to real EQ backend.

All actions return dict ok/error.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.eq")


class EqBridge(QObject):
    stateChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        self._player = player_service
        self._bypass = False
        self._presets = []
        self._current_preset = "Plano"
        self._preamp = 0.0
        self._backend_available = False

    @Property(bool, notify=stateChanged)
    def bypass(self):
        return self._bypass

    @Property(bool, notify=stateChanged)
    def backendAvailable(self):
        return self._backend_available

    @Property("QVariantList", notify=stateChanged)
    def presets(self):
        return self._presets

    @Property(str, notify=stateChanged)
    def currentPreset(self):
        return self._current_preset

    @Property(float, notify=stateChanged)
    def preamp(self):
        return self._preamp

    @Slot(result=dict)
    def refresh(self):
        try:
            from audio.eq_presets import get_preset_names, load_graphic_preset
            names = get_preset_names()
            self._presets = [{"name": n, "bands": load_graphic_preset(n) or []} for n in names]
            self._current_preset = names[0] if names else "Plano"
        except Exception:
            logger.debug("EQ refresh failed", exc_info=True)
            self._presets = [{"name": "Plano", "bands": [0.0] * 10}]
        self._backend_available = bool(self._player and hasattr(self._player, 'get_eq_state'))
        try:
            if self._backend_available:
                state = self._player.get_eq_state()
                if state:
                    self._bypass = state.get("bypass", False)
                    self._preamp = state.get("preamp", 0.0)
        except Exception:
            logger.debug("EQ state read failed", exc_info=True)
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def applyPreset(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        try:
            from audio.eq_presets import load_graphic_preset
            bands = load_graphic_preset(name)
            if bands and self._player and hasattr(self._player, 'set_eq_graphic'):
                self._player.set_eq_graphic(bands)
                self._current_preset = name
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "FAILED_TO_APPLY"}
        except Exception as e:
            logger.debug("EQ apply preset failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(bool, result=dict)
    def toggleBypass(self, enabled: bool):
        self._bypass = enabled
        try:
            if self._player and hasattr(self._player, 'set_eq_bypass'):
                self._player.set_eq_bypass(enabled)
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "NO_PLAYER"}
        except Exception as e:
            logger.debug("EQ bypass toggle failed", exc_info=True)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}

    @Slot(float, result=dict)
    def setPreamp(self, value: float):
        self._preamp = value
        try:
            if self._player and hasattr(self._player, 'set_eq_preamp'):
                self._player.set_eq_preamp(value)
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "NO_PLAYER"}
        except Exception as e:
            logger.debug("EQ preamp set failed", exc_info=True)
            self.stateChanged.emit()
            return {"ok": False, "error": str(e)}
