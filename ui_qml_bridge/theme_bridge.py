"""ThemeBridge — dynamic theme with dark/light/system, accent, high contrast, density.
Connected to ThemeStore for real-time QML theme updates.
Uses SettingsService for persistence instead of direct SETTINGS writes.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property

from core.settings_manager import SETTINGS


class ThemeBridge(QObject):
    themeChanged = Signal()

    def __init__(self, coordinator=None, service=None, parent=None):
        super().__init__(parent)
        self._coordinator = coordinator
        self._service = service
        self._theme = SETTINGS.value("appearance/theme", "dark")
        self._accent_color = SETTINGS.value("appearance/accent_color", "#8FB7FF")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._compact_mode = bool(SETTINGS.value("appearance/compact_mode", False))
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._dark_mode = self._theme != "light"

    def _set_via_service(self, key: str, value):
        if self._service:
            self._service.set_(key, value)
        elif self._coordinator:
            self._coordinator.execute(key, value)
        else:
            SETTINGS.setValue(key, value)
            SETTINGS.sync()

    def _notify_theme_store(self):
        try:
            from PySide6.QtQml import qmlEngine
            engine = qmlEngine(self)
            if engine:
                store = engine.singleton("ThemeStore")
                if store:
                    store.updateFromBridge(self)
        except Exception:
            pass

    @Property(bool, notify=themeChanged)
    def darkMode(self):
        return self._dark_mode

    @darkMode.setter
    def darkMode(self, enabled: bool):
        if enabled != self._dark_mode:
            self._dark_mode = enabled
            self._theme = "dark" if enabled else "light"
            self._set_via_service("appearance/theme", self._theme)
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, val: str):
        if val != self._theme:
            self._theme = val
            self._dark_mode = val != "light"
            self._set_via_service("appearance/theme", val)
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def accentColor(self):
        return self._accent_color

    @accentColor.setter
    def accentColor(self, color: str):
        if color != self._accent_color:
            self._accent_color = color
            self._set_via_service("appearance/accent_color", color)
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def highContrast(self):
        return self._high_contrast

    @highContrast.setter
    def highContrast(self, val: bool):
        if val != self._high_contrast:
            self._high_contrast = val
            self._set_via_service("accessibility/high_contrast", val)
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def compactMode(self):
        return self._compact_mode

    @compactMode.setter
    def compactMode(self, val: bool):
        if val != self._compact_mode:
            self._compact_mode = val
            self._set_via_service("appearance/compact_mode", val)
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def fontScale(self):
        return self._font_scale

    @fontScale.setter
    def fontScale(self, val: str):
        if val != self._font_scale:
            self._font_scale = val
            self._set_via_service("accessibility/font_size", val)
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def reduceMotion(self):
        return self._reduce_motion

    @reduceMotion.setter
    def reduceMotion(self, val: bool):
        if val != self._reduce_motion:
            self._reduce_motion = val
            self._set_via_service("accessibility/reduce_motion", val)
            self.themeChanged.emit()
