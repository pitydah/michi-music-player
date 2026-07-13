"""ThemeBridge — dynamic theme with dark/light/system, accent, high contrast, density."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property

from core.settings_manager import SETTINGS


class ThemeBridge(QObject):
    themeChanged = Signal()

    def __init__(self, coordinator=None, parent=None):
        super().__init__(parent)
        self._coordinator = coordinator
        self._theme = SETTINGS.value("appearance/theme", "dark")
        self._accent_color = SETTINGS.value("appearance/accent_color", "#8FB7FF")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._compact_mode = bool(SETTINGS.value("appearance/compact_mode", False))
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._dark_mode = self._theme != "light"

    @Property(bool, notify=themeChanged)
    def darkMode(self):
        return self._dark_mode

    @darkMode.setter
    def darkMode(self, enabled: bool):
        if enabled != self._dark_mode:
            self._dark_mode = enabled
            self._theme = "dark" if enabled else "light"
            SETTINGS.setValue("appearance/theme", self._theme)
            SETTINGS.sync()
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, val: str):
        if val != self._theme:
            self._theme = val
            self._dark_mode = val != "light"
            if self._coordinator:
                self._coordinator.apply("appearance/theme", val)
            else:
                SETTINGS.setValue("appearance/theme", val)
                SETTINGS.sync()
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def accentColor(self):
        return self._accent_color

    @accentColor.setter
    def accentColor(self, color: str):
        self._accent_color = color
        if self._coordinator:
            self._coordinator.apply("appearance/accent_color", color)
        else:
            SETTINGS.setValue("appearance/accent_color", color)
            SETTINGS.sync()
        self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def highContrast(self):
        return self._high_contrast

    @highContrast.setter
    def highContrast(self, val: bool):
        self._high_contrast = val
        if self._coordinator:
            self._coordinator.apply("accessibility/high_contrast", val)
        else:
            SETTINGS.setValue("accessibility/high_contrast", val)
            SETTINGS.sync()
        self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def compactMode(self):
        return self._compact_mode

    @compactMode.setter
    def compactMode(self, val: bool):
        self._compact_mode = val
        if self._coordinator:
            self._coordinator.apply("appearance/compact_mode", val)
        else:
            SETTINGS.setValue("appearance/compact_mode", val)
            SETTINGS.sync()
        self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def fontScale(self):
        return self._font_scale

    @fontScale.setter
    def fontScale(self, val: str):
        self._font_scale = val
        if self._coordinator:
            self._coordinator.apply("accessibility/font_size", val)
        else:
            SETTINGS.setValue("accessibility/font_size", val)
            SETTINGS.sync()
        self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def reduceMotion(self):
        return self._reduce_motion

    @reduceMotion.setter
    def reduceMotion(self, val: bool):
        self._reduce_motion = val
        if self._coordinator:
            self._coordinator.apply("accessibility/reduce_motion", val)
        else:
            SETTINGS.setValue("accessibility/reduce_motion", val)
            SETTINGS.sync()
        self.themeChanged.emit()
