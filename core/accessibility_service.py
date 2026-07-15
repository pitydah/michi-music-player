"""AccessibilityService — runtime accessibility audit and support."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.accessibility")


class AccessibilityService:
    def __init__(self):
        self._enabled = True
        self._font_scale = 1.0
        self._reduced_motion = False
        self._high_contrast = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    @property
    def font_scale(self) -> float:
        return self._font_scale

    def set_font_scale(self, scale: float):
        self._font_scale = max(0.5, min(2.0, scale))

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    def set_reduced_motion(self, enabled: bool):
        self._reduced_motion = enabled

    @property
    def high_contrast(self) -> bool:
        return self._high_contrast

    def set_high_contrast(self, enabled: bool):
        self._high_contrast = enabled

    def health(self) -> dict:
        return {
            "available": True,
            "font_scale": self._font_scale,
            "reduced_motion": self._reduced_motion,
            "high_contrast": self._high_contrast,
        }

    def shutdown(self):
        pass
