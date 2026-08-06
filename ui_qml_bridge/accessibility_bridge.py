"""AccessibilityBridge — thin QML adapter over the canonical AccessibilityService.

No QSettings access and no independent state: the service owns accessibility
state, persistence and signals; this bridge re-exposes them to QML and
re-emits the service signals (ADR-002, S11). The bridge keeps one side
effect: applying ``mono``/``balance`` to the playback service, which only the
UI layer can own.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

_instance = None

logger = logging.getLogger(__name__)


class AccessibilityBridge(QObject):
    dataChanged = Signal()

    def __init__(self, service=None, coordinator=None, playback_service=None,
                 settings_service=None, settings_coordinator=None, parent=None):
        global _instance
        super().__init__(parent)
        _instance = self
        logger.debug("AccessibilityBridge.__init__ called")
        self._svc = service or settings_service or coordinator or settings_coordinator
        self._playback_service = playback_service
        self._last_error = ""
        if self._svc is None:
            logger.warning("AccessibilityBridge: service is None — running in degraded mode")
        else:
            if hasattr(self._svc, "register_consumer"):
                self._svc.register_consumer("accessibility_bridge")
            if hasattr(self._svc, "stateChanged") and hasattr(
                    self._svc.stateChanged, "connect"):
                self._svc.stateChanged.connect(self._on_service_state)

        self._apply_mono_to_playback()
        self._apply_balance_to_playback()

    # ── Service state access ──

    def _svc_attr(self, name, default):
        if self._svc is None:
            return default
        return getattr(self._svc, name, default)

    def _on_service_state(self, *_args):
        self._apply_mono_to_playback()
        self._apply_balance_to_playback()
        self.dataChanged.emit()

    def _apply_mono_to_playback(self):
        if self._playback_service and hasattr(self._playback_service, 'set_mono'):
            try:
                self._playback_service.set_mono(self.mono)
                self._last_error = ""
            except Exception:
                self._last_error = "Backend rejected mono change"
                self.dataChanged.emit()

    def _apply_balance_to_playback(self):
        if self._playback_service and hasattr(self._playback_service, 'set_balance'):
            try:
                self._playback_service.set_balance(self.balance)
                self._last_error = ""
            except Exception as e:
                self._last_error = str(e)
                self.dataChanged.emit()

    def _restore_visual_control(self):
        self.mono = False
        self.balance = 0

    @Property(float, notify=dataChanged)
    def fontScale(self):
        return float(self._svc_attr("font_scale", 1.0))

    @fontScale.setter
    def fontScale(self, val: float):
        if self._svc is not None and hasattr(self._svc, "set_font_scale"):
            self._svc.set_font_scale(float(val))
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def highContrast(self):
        return bool(self._svc_attr("high_contrast", False))

    @highContrast.setter
    def highContrast(self, val: bool):
        if self._svc is not None and hasattr(self._svc, "set_high_contrast"):
            self._svc.set_high_contrast(bool(val))
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def reduceMotion(self):
        return bool(self._svc_attr("reduced_motion", False))

    @reduceMotion.setter
    def reduceMotion(self, val: bool):
        if self._svc is not None and hasattr(self._svc, "set_reduced_motion"):
            self._svc.set_reduced_motion(bool(val))
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def reduceTransparency(self):
        return bool(self._svc_attr("reduce_transparency", False))

    @reduceTransparency.setter
    def reduceTransparency(self, val: bool):
        if self._svc is not None and hasattr(self._svc, "set_reduce_transparency"):
            self._svc.set_reduce_transparency(bool(val))
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def focusIndicators(self):
        return bool(self._svc_attr("focus_indicators", True))

    @focusIndicators.setter
    def focusIndicators(self, val: bool):
        if self._svc is not None and hasattr(self._svc, "set_focus_indicators"):
            self._svc.set_focus_indicators(bool(val))
            self.dataChanged.emit()

    @Property(bool, notify=dataChanged)
    def mono(self):
        return bool(self._svc_attr("mono", False))

    @mono.setter
    def mono(self, val: bool):
        old = self.mono
        if self._svc is not None and hasattr(self._svc, "set_mono"):
            self._svc.set_mono(bool(val))
        self._apply_mono_to_playback()
        if (self._last_error or not self._playback_service) and self._svc is not None \
                and hasattr(self._svc, "set_mono"):
            # Backend rejection (or absence) reverts the control.
            self._svc.set_mono(old)
        self.dataChanged.emit()

    @Property(float, notify=dataChanged)
    def balance(self):
        return float(self._svc_attr("balance", 0.0))

    @balance.setter
    def balance(self, val: float):
        if self._svc is not None and hasattr(self._svc, "set_balance"):
            self._svc.set_balance(float(val))
        self._apply_balance_to_playback()
        if self._last_error and self._svc is not None and hasattr(self._svc, "set_balance"):
            self._svc.set_balance(0.0)
        self.dataChanged.emit()

    @Slot(result=dict)
    def restoreOnError(self):
        self._restore_visual_control()
        return {"ok": True, "mono": False, "balance": 0.0}

    @Property(str, notify=dataChanged)
    def lastError(self):
        return self._last_error

    @Slot(result=dict)
    def accessibilityScore(self) -> dict:
        score = 0
        if self.fontScale:
            score += 10
        if self.highContrast:
            score += 10
        if self.focusIndicators:
            score += 10
        if self.reduceMotion:
            score += 10
        if self.reduceTransparency:
            score += 10
        if not self.mono:
            score += 10
        if self.balance != 0:
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
            "font_scale": self.fontScale,
            "high_contrast": self.highContrast,
            "reduce_motion": self.reduceMotion,
            "reduce_transparency": self.reduceTransparency,
            "focus_indicators": self.focusIndicators,
            "mono": self.mono,
            "balance": self.balance,
            "has_playback_service": self._playback_service is not None,
        }

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
