"""EqBridge — connects QML EQ page to real EQ backend.

Includes: enable, bypass, graphic bands, parametric bands, preamp, presets,
reset, import/export, backend restrictions, bit-perfect conflict,
persistencia, runtime state.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.eq")

GRAPHIC_BAND_COUNT = 10
PARAMETRIC_BAND_COUNT = 6
DEFAULT_GRAPHIC_FREQS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


class EqBridge(QObject):
    stateChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        assert player_service is not None, "EqBridge: player_service is REQUIRED"
        self._player = player_service
        self._enabled = True
        self._bypass = False
        self._presets: list[dict] = []
        self._current_preset = "Plano"
        self._preamp = 0.0
        self._graphic_bands: list[float] = [0.0] * GRAPHIC_BAND_COUNT
        self._parametric_bands: list[dict] = [
            {"freq": 32, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
            {"freq": 64, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
            {"freq": 125, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
            {"freq": 250, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
            {"freq": 500, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
            {"freq": 1000, "gain": 0, "q": 0.7, "type": "peaking", "enabled": False},
        ]
        self._backend_available = False
        self._bitperfect_conflict = False
        self._backend_restrictions: dict[str, Any] = {}

    @Property(bool, notify=stateChanged)
    def enabled(self):
        return self._enabled

    @Property(bool, notify=stateChanged)
    def bypass(self):
        return self._bypass

    @Property(bool, notify=stateChanged)
    def backendAvailable(self):
        return self._backend_available

    @Property(bool, notify=stateChanged)
    def bitperfectConflict(self):
        return self._bitperfect_conflict

    @Property("QVariantList", notify=stateChanged)
    def presets(self):
        return list(self._presets)

    @Property(str, notify=stateChanged)
    def currentPreset(self):
        return self._current_preset

    @Property(float, notify=stateChanged)
    def preamp(self):
        return self._preamp

    @Property("QVariantList", notify=stateChanged)
    def graphicBands(self):
        return [{"freq": DEFAULT_GRAPHIC_FREQS[i], "gain": self._graphic_bands[i]}
                for i in range(GRAPHIC_BAND_COUNT)]

    @Property("QVariantList", notify=stateChanged)
    def parametricBands(self):
        return list(self._parametric_bands)

    def _update_backend_state(self):
        self._backend_available = bool(self._player and hasattr(self._player, 'get_eq_state'))
        self._bitperfect_conflict = False
        self._backend_restrictions = {}
        if self._backend_available:
            try:
                state = self._player.get_eq_state()
                if state:
                    self._bypass = state.get("bypass", False)
                    self._preamp = state.get("preamp", 0.0)
                    self._enabled = not self._bypass
                    gb = state.get("graphic_bands")
                    if gb and len(gb) == GRAPHIC_BAND_COUNT:
                        self._graphic_bands = list(gb)
            except Exception:
                logger.debug("EQ state read failed", exc_info=True)
            try:
                if hasattr(self._player, 'get_active_backend_id'):
                    bid = self._player.get_active_backend_id()
                    if bid and "mpd" in str(bid).lower():
                        self._bitperfect_conflict = True
                        self._backend_restrictions["reason"] = "MPD backend bloquea EQ"
            except Exception:
                pass

    @Slot(result=dict)
    def refresh(self):
        try:
            from audio.eq_presets import get_preset_names, load_graphic_preset
            names = get_preset_names()
            self._presets = [{"name": n, "bands": load_graphic_preset(n) or [0.0] * GRAPHIC_BAND_COUNT}
                             for n in names]
            if names:
                self._current_preset = names[0]
        except Exception:
            logger.debug("EQ refresh failed", exc_info=True)
            self._presets = [{"name": "Plano", "bands": [0.0] * GRAPHIC_BAND_COUNT}]
        self._update_backend_state()
        self.stateChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def applyPreset(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        if self._bitperfect_conflict:
            return {"ok": False, "error": "BITPERFECT_CONFLICT",
                    "message": "EQ bloqueado en modo bit-perfect"}
        try:
            from audio.eq_presets import load_graphic_preset
            bands = load_graphic_preset(name)
            if bands and self._player and hasattr(self._player, 'set_eq_graphic'):
                self._player.set_eq_graphic(bands)
                self._graphic_bands = list(bands) if len(bands) == GRAPHIC_BAND_COUNT else [0.0] * GRAPHIC_BAND_COUNT
                self._current_preset = name
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "FAILED_TO_APPLY"}
        except Exception as e:
            logger.debug("EQ apply preset failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(bool, result=dict)
    def setEnabled(self, enabled: bool):
        self._enabled = enabled
        if self._bitperfect_conflict and enabled:
            return {"ok": False, "error": "BITPERFECT_CONFLICT",
                    "message": "EQ bloqueado en modo bit-perfect"}
        return self.toggleBypass(not enabled)

    @Slot(bool, result=dict)
    def toggleBypass(self, enabled: bool):
        if self._bitperfect_conflict:
            return {"ok": False, "error": "BITPERFECT_CONFLICT",
                    "message": "EQ bloqueado en modo bit-perfect"}
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

    @Slot(int, float, result=dict)
    def setGraphicBand(self, index: int, gain: float):
        if index < 0 or index >= GRAPHIC_BAND_COUNT:
            return {"ok": False, "error": "INVALID_INDEX"}
        if self._bitperfect_conflict:
            return {"ok": False, "error": "BITPERFECT_CONFLICT"}
        self._graphic_bands[index] = max(-24, min(24, gain))
        try:
            if self._player and hasattr(self._player, 'set_eq_graphic'):
                self._player.set_eq_graphic(self._graphic_bands)
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "NO_PLAYER"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, str, float, float, bool, result=dict)
    def setParametricBand(self, index: int, band_type: str, freq: float,
                          gain: float, enabled: bool):
        if index < 0 or index >= PARAMETRIC_BAND_COUNT:
            return {"ok": False, "error": "INVALID_INDEX"}
        if self._bitperfect_conflict:
            return {"ok": False, "error": "BITPERFECT_CONFLICT"}
        self._parametric_bands[index] = {
            "freq": freq, "gain": max(-24, min(24, gain)),
            "q": 0.7, "type": band_type or "peaking", "enabled": enabled,
        }
        try:
            if self._player and hasattr(self._player, 'set_eq_parametric'):
                self._player.set_eq_parametric(self._parametric_bands)
                self.stateChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "NO_PLAYER"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def reset(self):
        self._graphic_bands = [0.0] * GRAPHIC_BAND_COUNT
        self._preamp = 0.0
        self._bypass = False
        self._enabled = True
        for b in self._parametric_bands:
            b["gain"] = 0
            b["enabled"] = False
        try:
            if self._player:
                if hasattr(self._player, 'set_eq_graphic'):
                    self._player.set_eq_graphic(self._graphic_bands)
                if hasattr(self._player, 'set_eq_preamp'):
                    self._player.set_eq_preamp(0.0)
                if hasattr(self._player, 'set_eq_bypass'):
                    self._player.set_eq_bypass(False)
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def importPreset(self, filepath: str):
        try:
            p = Path(filepath)
            if not p.is_file():
                return {"ok": False, "error": "FILE_NOT_FOUND"}
            data = json.loads(p.read_text())
            bands = data.get("bands", [])
            if len(bands) != GRAPHIC_BAND_COUNT:
                return {"ok": False, "error": "INVALID_BAND_COUNT"}
            name = data.get("name", p.stem)
            from audio.eq_presets import save_custom_presets, load_custom_presets
            custom = load_custom_presets()
            custom[name] = bands
            save_custom_presets(custom)
            self._presets.append({"name": name, "bands": bands})
            self.stateChanged.emit()
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def exportPreset(self, filepath: str):
        try:
            data = json.dumps({
                "name": self._current_preset,
                "bands": self._graphic_bands,
                "preamp": self._preamp,
                "bypass": self._bypass,
            }, indent=2)
            Path(filepath).write_text(data)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def saveState(self):
        try:
            from core.settings_manager import set_
            set_("audio/eq_enabled", self._enabled)
            set_("audio/eq_bypass", self._bypass)
            set_("audio/eq_preamp", self._preamp)
            set_("audio/eq_preset", self._current_preset)
            set_("audio/eq_graphic_bands", json.dumps(self._graphic_bands))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def saveCustomPreset(self, name: str):
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        try:
            from audio.eq_presets import save_custom_presets, load_custom_presets
            custom = load_custom_presets()
            custom[name] = list(self._graphic_bands)
            save_custom_presets(custom)
            self._presets.append({"name": name, "bands": list(self._graphic_bands)})
            self.stateChanged.emit()
            return {"ok": True, "name": name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def restoreState(self):
        try:
            from core.settings_manager import get
            self._enabled = get("audio/eq_enabled", True)
            self._bypass = get("audio/eq_bypass", False)
            self._preamp = get("audio/eq_preamp", 0.0)
            self._current_preset = get("audio/eq_preset", "Plano")
            bands_json = get("audio/eq_graphic_bands", "[]")
            bands = json.loads(bands_json)
            if len(bands) == GRAPHIC_BAND_COUNT:
                self._graphic_bands = bands
            self.stateChanged.emit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
