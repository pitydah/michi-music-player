"""AccessibilityService — canonical owner of accessibility state.

Single authority per ADR-002: font scale, high contrast, reduced motion,
reduce transparency, focus indicators, mono and balance live HERE; QSettings
persistence happens only through this service (single write path); QML
bridges are thin adapters that re-expose the service state and re-emit its
signals. ``health()`` reports operational state plus the number of registered
UI consumers, so health honestly reflects whether the UI consumes the
service.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.accessibility")

MIN_FONT_SCALE = 0.5
MAX_FONT_SCALE = 2.0


class AccessibilityService(QObject):
    stateChanged = Signal()
    fontScaleChanged = Signal(float)
    highContrastChanged = Signal(bool)
    reducedMotionChanged = Signal(bool)

    def __init__(self, settings=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._enabled = True
        self._font_scale = 1.0
        self._reduced_motion = False
        self._high_contrast = False
        self._reduce_transparency = False
        self._focus_indicators = True
        self._mono = False
        self._balance = 0.0
        self._consumers: dict[str, bool] = {}
        self._last_persisted_ok = True
        self._last_persist_error = ""
        self._load_persisted()

    # ── Persistence (single write path) ──

    def _read(self, key: str, default: Any) -> Any:
        settings = self._settings
        if settings is None:
            try:
                from core.settings_manager import get
                return get(key)
            except Exception:
                return default
        try:
            value = settings.value(key, default)
            return default if value is None else value
        except Exception:
            return default

    def _write(self, key: str, value: Any) -> None:
        try:
            settings = self._settings
            if settings is None:
                from core.settings_manager import set_
                set_(key, value)
            else:
                settings.setValue(key, value)
            self._last_persisted_ok = True
            self._last_persist_error = ""
        except Exception as exc:
            self._last_persisted_ok = False
            self._last_persist_error = str(exc)[:200]
            logger.error("AccessibilityService: failed to persist '%s': %s", key, exc)

    def _load_persisted(self) -> None:
        try:
            self._font_scale = self._clamp_scale(float(self._read("accessibility/font_size", 1.0)))
        except (TypeError, ValueError):
            self._font_scale = 1.0
        try:
            self._high_contrast = bool(self._read("accessibility/high_contrast", False))
        except Exception:
            self._high_contrast = False
        try:
            self._reduced_motion = bool(self._read("accessibility/reduced_motion", False))
        except Exception:
            self._reduced_motion = False
        try:
            self._reduce_transparency = bool(self._read("accessibility/reduce_transparency", False))
        except Exception:
            self._reduce_transparency = False
        try:
            self._focus_indicators = bool(self._read("accessibility/focus_indicators", True))
        except Exception:
            self._focus_indicators = True
        try:
            self._mono = bool(self._read("accessibility/mono", False))
        except Exception:
            self._mono = False
        try:
            self._balance = max(-1.0, min(1.0, float(self._read("accessibility/balance", 0.0))))
        except (TypeError, ValueError):
            self._balance = 0.0

    @staticmethod
    def _clamp_scale(scale: float) -> float:
        return max(MIN_FONT_SCALE, min(MAX_FONT_SCALE, scale))

    # ── State ──

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def font_scale(self) -> float:
        return self._font_scale

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    @property
    def high_contrast(self) -> bool:
        return self._high_contrast

    @property
    def reduce_transparency(self) -> bool:
        return self._reduce_transparency

    @property
    def focus_indicators(self) -> bool:
        return self._focus_indicators

    @property
    def mono(self) -> bool:
        return self._mono

    @property
    def balance(self) -> float:
        return self._balance

    # ── Setters (persist + emit; single write path) ──

    def set_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self.stateChanged.emit()

    def set_font_scale(self, scale: float):
        scale = self._clamp_scale(float(scale))
        if scale == self._font_scale:
            return
        self._font_scale = scale
        self._write("accessibility/font_size", scale)
        self.fontScaleChanged.emit(scale)
        self.stateChanged.emit()

    def set_reduced_motion(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._reduced_motion:
            return
        self._reduced_motion = enabled
        self._write("accessibility/reduced_motion", enabled)
        self.reducedMotionChanged.emit(enabled)
        self.stateChanged.emit()

    def set_high_contrast(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._high_contrast:
            return
        self._high_contrast = enabled
        self._write("accessibility/high_contrast", enabled)
        self.highContrastChanged.emit(enabled)
        self.stateChanged.emit()

    def set_reduce_transparency(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._reduce_transparency:
            return
        self._reduce_transparency = enabled
        self._write("accessibility/reduce_transparency", enabled)
        self.stateChanged.emit()

    def set_focus_indicators(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._focus_indicators:
            return
        self._focus_indicators = enabled
        self._write("accessibility/focus_indicators", enabled)
        self.stateChanged.emit()

    def set_mono(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._mono:
            return
        self._mono = enabled
        self._write("accessibility/mono", enabled)
        self.stateChanged.emit()

    def set_balance(self, value: float):
        value = max(-1.0, min(1.0, float(value)))
        if value == self._balance:
            return
        self._balance = value
        self._write("accessibility/balance", value)
        self.stateChanged.emit()

    # ── Consumers (health: does the UI actually consume this service?) ──

    def register_consumer(self, name: str) -> None:
        self._consumers[name] = True
        logger.debug("AccessibilityService: consumer '%s' registered", name)

    def unregister_consumer(self, name: str) -> None:
        self._consumers.pop(name, None)

    @property
    def consumer_count(self) -> int:
        return len(self._consumers)

    # ── Health ──

    def health(self) -> dict:
        settings_ok = True
        try:
            self._read("accessibility/font_size", 1.0)
        except Exception:
            settings_ok = False
        return {
            "available": True,
            "operational": self._enabled,
            "settings_ok": settings_ok,
            "last_persisted_ok": self._last_persisted_ok,
            "last_persist_error": self._last_persist_error,
            "consumers": self.consumer_count,
            "font_scale": self._font_scale,
            "reduced_motion": self._reduced_motion,
            "high_contrast": self._high_contrast,
            "reduce_transparency": self._reduce_transparency,
            "focus_indicators": self._focus_indicators,
            "mono": self._mono,
            "balance": self._balance,
        }

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
