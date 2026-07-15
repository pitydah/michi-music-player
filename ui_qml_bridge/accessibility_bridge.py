from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.settings_manager import SETTINGS


class AccessibilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, service=None, coordinator=None, playback_service=None,
                 settings_service=None, settings_coordinator=None, parent=None):
        super().__init__(parent)
        assert playback_service is not None, "AccessibilityBridge: playback_service is REQUIRED"
        self._svc = service or settings_service
        self._coordinator = coordinator or settings_coordinator
        self._playback_service = playback_service
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._focus_indicators = bool(SETTINGS.value("accessibility/focus_indicators", True))
        self._mono = bool(SETTINGS.value("accessibility/mono", False))
        self._balance = int(SETTINGS.value("accessibility/balance", 0))
        self._last_error = ""
        self._reduce_transparency = bool(SETTINGS.value("accessibility/reduce_transparency", False))

    def _set_via_service(self, key: str, value):
        if self._svc:
            self._svc.set_(key, value)
        elif self._coordinator:
            self._coordinator.execute(key, value)
        else:
            SETTINGS.setValue(key, value)
            SETTINGS.sync()

    def _apply_mono_to_playback(self):
        if self._playback_service and hasattr(self._playback_service, 'set_mono'):
            try:
                self._playback_service.set_mono(self._mono)
                self._last_error = ""
            except Exception:
                self._mono = not self._mono
                self._last_error = "Backend rejected mono change"
                self.dataChanged.emit()

    def _apply_balance_to_playback(self):
        if self._playback_service and hasattr(self._playback_service, 'set_balance'):
            try:
                self._playback_service.set_balance(self._balance)
                self._last_error = ""
            except Exception as e:
                self._last_error = str(e)
                self._balance = 0
                self.dataChanged.emit()

    def _restore_visual_control(self):
        self.mono = False
        self.balance = 0

    @Property(str, notify=dataChanged)
    def fontScale(self):
        return self._font_scale

    @fontScale.setter
    def fontScale(self, val: str):
        if val != self._font_scale:
            self._font_scale = val
            self._set_via_service("accessibility/font_size", val)
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def highContrast(self):
        return self._high_contrast

    @highContrast.setter
    def highContrast(self, val: bool):
        if val != self._high_contrast:
            self._high_contrast = val
            self._set_via_service("accessibility/high_contrast", val)
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def reduceMotion(self):
        return self._reduce_motion

    @reduceMotion.setter
    def reduceMotion(self, val: bool):
        if val != self._reduce_motion:
            self._reduce_motion = val
            self._set_via_service("accessibility/reduce_motion", val)
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def reduceTransparency(self):
        return self._reduce_transparency

    @reduceTransparency.setter
    def reduceTransparency(self, val: bool):
        if val != self._reduce_transparency:
            self._reduce_transparency = val
            self._set_via_service("accessibility/reduce_transparency", val)
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def focusIndicators(self):
        return self._focus_indicators

    @focusIndicators.setter
    def focusIndicators(self, val: bool):
        if val != self._focus_indicators:
            self._focus_indicators = val
            self._set_via_service("accessibility/focus_indicators", val)
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def mono(self):
        return self._mono

    @mono.setter
    def mono(self, val: bool):
        if val != self._mono:
            old = self._mono
            self._mono = val
            self._set_via_service("accessibility/mono", val)
            self._apply_mono_to_playback()
            if not self._playback_service:
                self._mono = old
            self.dataChanged.emit()

    @Property(int, notify=dataChanged)
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, val: int):
        if val != self._balance:
            self._balance = max(-100, min(100, val))
            self._set_via_service("accessibility/balance", self._balance)
            self._apply_balance_to_playback()
            self.dataChanged.emit()

    @Slot(result=dict)
    def restoreOnError(self):
        self._restore_visual_control()
        return {"ok": True, "mono": False, "balance": 0}

    @Property(str, notify=dataChanged)
    def lastError(self):
        return self._last_error

    @Slot(result=dict)
    def accessibilityScore(self) -> dict:
        score = 0
        if self._font_scale:
            score += 10
        if self._high_contrast:
            score += 10
        if self._focus_indicators:
            score += 10
        if self._reduce_motion:
            score += 10
        if self._reduce_transparency:
            score += 10
        if not self._mono:
            score += 10
        if self._balance != 0:
            score += 10
        if self._playback_service:
            score += 20
        try:
            from core.settings_schema import ALL_CATEGORIES
            for cat in ALL_CATEGORIES:
                if cat.id == "accessibility":
                    score += 20
                    break
        except Exception:
            pass
        return {
            "score": min(100, score),
            "font_scale": self._font_scale,
            "high_contrast": self._high_contrast,
            "reduce_motion": self._reduce_motion,
            "reduce_transparency": self._reduce_transparency,
            "focus_indicators": self._focus_indicators,
            "mono": self._mono,
            "balance": self._balance,
            "has_playback_service": self._playback_service is not None,
        }

    @Slot()
    def refresh(self):
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._reduce_transparency = bool(SETTINGS.value("accessibility/reduce_transparency", False))
        self._focus_indicators = bool(SETTINGS.value("accessibility/focus_indicators", True))
        self._mono = bool(SETTINGS.value("accessibility/mono", False))
        self._balance = int(SETTINGS.value("accessibility/balance", 0))
        self.dataChanged.emit()
