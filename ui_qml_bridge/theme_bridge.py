"""ThemeBridge — thin QML adapter over the canonical ThemeService.

No QSettings access and no independent state: the service owns theme state,
persistence and signals; this bridge only re-exposes them to QML and re-emits
the service signals (ADR-002, S11). Accessibility values exposed for the
ThemeStore (``reducedMotion``/``highContrast``/...) delegate to the canonical
``AccessibilityService``.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

_instance = None
logger = logging.getLogger("michi.theme_bridge")

DEFAULT_THEME = "dark"
DEFAULT_ACCENT = "#8FB7FF"


class ThemeBridge(QObject):
    """Expose the canonical theme service state to QML (thin adapter)."""

    themeChanged = Signal()
    highContrastChanged = Signal(bool)

    VALID_THEMES = ("dark", "light", "system", "high_contrast")

    def __init__(
        self,
        service: Any | None = None,
        coordinator: Any | None = None,
        accessibility_service: Any | None = None,
        parent: QObject | None = None,
    ) -> None:
        global _instance
        super().__init__(parent)
        _instance = self
        self._service = service or coordinator
        self._accessibility_service = accessibility_service
        if self._service is None:
            logger.warning("ThemeBridge: service is None — running in degraded mode")
        else:
            if hasattr(self._service, "register_consumer"):
                self._service.register_consumer("theme_bridge")
            for signal_name, forward in (
                ("themeChanged", self._on_service_theme),
                ("accentChanged", self._on_service_accent),
                ("compactModeChanged", self._on_service_compact),
            ):
                sig = getattr(self._service, signal_name, None)
                if sig is not None and hasattr(sig, "connect"):
                    sig.connect(forward)
        if self._accessibility_service is not None and hasattr(
                self._accessibility_service, "register_consumer"):
            self._accessibility_service.register_consumer("theme_bridge")
            self._accessibility_service.stateChanged.connect(self._on_service_state)
            high_contrast_sig = getattr(
                self._accessibility_service, "highContrastChanged", None)
            if high_contrast_sig is not None and hasattr(high_contrast_sig, "connect"):
                high_contrast_sig.connect(self.highContrastChanged.emit)

    # ── Service signal forwarding ──

    def _on_service_theme(self, *_args):
        self.themeChanged.emit()

    def _on_service_accent(self, *_args):
        self.themeChanged.emit()

    def _on_service_compact(self, *_args):
        self.themeChanged.emit()

    def _on_service_state(self, *_args):
        self.themeChanged.emit()

    # ── Service state access ──

    def _state(self) -> Any:
        return self._service

    def _a11y(self) -> Any:
        return self._accessibility_service

    def _notify_theme_store(self):
        try:
            from PySide6.QtQml import qmlEngine
            engine = qmlEngine(self)
            if engine:
                store = engine.singleton("ThemeStore")
                if store and hasattr(store, 'updateFromBridge'):
                    store.updateFromBridge(self)
        except Exception:
            logger.exception("ThemeBridge: failed to notify ThemeStore")

    @Property(bool, notify=themeChanged)
    def darkMode(self):
        service = self._state()
        if service is not None and hasattr(service, "dark_mode"):
            return service.dark_mode
        return DEFAULT_THEME != "light"

    @darkMode.setter
    def darkMode(self, enabled: bool):
        service = self._state()
        if service is None:
            return
        if hasattr(service, "set_theme"):
            service.set_theme("dark" if enabled else "light")

    @Property(str, notify=themeChanged)
    def theme(self):
        service = self._state()
        if service is not None and hasattr(service, "theme"):
            return service.theme
        return DEFAULT_THEME

    @theme.setter
    def theme(self, val: str):
        service = self._state()
        if service is None:
            return
        if hasattr(service, "set_theme"):
            service.set_theme(val)

    @Property(str, notify=themeChanged)
    def accentColor(self):
        service = self._state()
        if service is not None and hasattr(service, "accent_color"):
            return service.accent_color
        return DEFAULT_ACCENT

    @accentColor.setter
    def accentColor(self, color: str):
        service = self._state()
        if service is None:
            return
        if hasattr(service, "set_accent_color"):
            service.set_accent_color(color)

    @Property(bool, notify=highContrastChanged)
    def highContrast(self):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "high_contrast"):
            return a11y.high_contrast
        return False

    @highContrast.setter
    def highContrast(self, val: bool):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "set_high_contrast"):
            a11y.set_high_contrast(bool(val))
            self.highContrastChanged.emit(bool(val))

    @Property(bool, notify=themeChanged)
    def compactMode(self):
        service = self._state()
        if service is not None and hasattr(service, "compact_mode"):
            return service.compact_mode
        return False

    @compactMode.setter
    def compactMode(self, val: bool):
        service = self._state()
        if service is None:
            return
        if hasattr(service, "set_compact_mode"):
            service.set_compact_mode(bool(val))

    @Property(float, notify=themeChanged)
    def fontScale(self):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "font_scale"):
            return float(a11y.font_scale)
        return 1.0

    @fontScale.setter
    def fontScale(self, val: float):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "set_font_scale"):
            a11y.set_font_scale(float(val))

    @Property(bool, notify=themeChanged)
    def reducedMotion(self):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "reduced_motion"):
            return a11y.reduced_motion
        return False

    @reducedMotion.setter
    def reducedMotion(self, val: bool):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "set_reduced_motion"):
            a11y.set_reduced_motion(bool(val))

    @Property(float, notify=themeChanged)
    def animationScale(self) -> float:
        """Return the global animation multiplier for the current motion setting."""
        return 0.0 if self.reducedMotion else 1.0

    @Property(bool, notify=themeChanged)
    def reduceTransparency(self):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "reduce_transparency"):
            return a11y.reduce_transparency
        return False

    @reduceTransparency.setter
    def reduceTransparency(self, val: bool):
        a11y = self._a11y()
        if a11y is not None and hasattr(a11y, "set_reduce_transparency"):
            a11y.set_reduce_transparency(bool(val))

    @Slot(result=dict)
    def themeInfo(self):
        return {
            "theme": self.theme,
            "dark_mode": self.darkMode,
            "accent_color": self.accentColor,
            "high_contrast": self.highContrast,
            "reduced_motion": self.reducedMotion,
            "reduce_transparency": self.reduceTransparency,
            "valid_themes": list(self.VALID_THEMES),
        }
