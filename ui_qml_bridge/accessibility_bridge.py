"""AccessibilityBridge — accessibility state and scoring for QML."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.settings_manager import SETTINGS


class AccessibilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._focus_indicators = bool(SETTINGS.value("accessibility/focus_indicators", True))
        self._mono = bool(SETTINGS.value("accessibility/mono", False))
        self._balance = int(SETTINGS.value("accessibility/balance", 0))

    @Property(str, notify=dataChanged)
    def fontScale(self):
        return self._font_scale

    @Property(bool, notify=dataChanged)
    def highContrast(self):
        return self._high_contrast

    @Property(bool, notify=dataChanged)
    def reduceMotion(self):
        return self._reduce_motion

    @Property(bool, notify=dataChanged)
    def focusIndicators(self):
        return self._focus_indicators

    @Property(bool, notify=dataChanged)
    def mono(self):
        return self._mono

    @Property(int, notify=dataChanged)
    def balance(self):
        return self._balance

    @Slot(result=dict)
    def accessibilityScore(self) -> dict:
        score = 0
        if self._font_scale:
            score += 15
        if self._high_contrast:
            score += 15
        if self._focus_indicators:
            score += 15
        if self._reduce_motion:
            score += 15
        if not self._mono:
            score += 10
        if self._balance != 0:
            score += 10
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
            "focus_indicators": self._focus_indicators,
            "mono": self._mono,
            "balance": self._balance,
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
