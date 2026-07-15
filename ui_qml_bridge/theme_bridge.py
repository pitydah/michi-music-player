from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.settings_manager import SETTINGS


class ThemeBridge(QObject):
    themeChanged = Signal()

    VALID_THEMES = ("dark", "light", "system", "high_contrast")

    def __init__(self, service=None, coordinator=None, parent=None):
        super().__init__(parent)
        assert coordinator is not None, "ThemeBridge: coordinator is REQUIRED"
        self._service = service or coordinator
        self._theme = SETTINGS.value("appearance/theme", "dark")
        self._accent_color = SETTINGS.value("appearance/accent_color", "#8FB7FF")
        self._high_contrast = bool(SETTINGS.value("accessibility/high_contrast", False))
        self._compact_mode = bool(SETTINGS.value("appearance/compact_mode", False))
        self._font_scale = SETTINGS.value("accessibility/font_size", "normal")
        self._reduce_motion = bool(SETTINGS.value("accessibility/reduce_motion", False))
        self._reduce_transparency = bool(SETTINGS.value("accessibility/reduce_transparency", False))
        self._dark_mode = self._theme not in ("light",)

    def _write(self, key: str, value):
        if self._service and hasattr(self._service, 'set_'):
            self._service.set_(key, value)
        else:
            SETTINGS.setValue(key, value)
            SETTINGS.sync()

    def _notify_theme_store(self):
        try:
            from PySide6.QtQml import qmlEngine
            engine = qmlEngine(self)
            if engine:
                store = engine.singleton("ThemeStore")
                if store and hasattr(store, 'updateFromBridge'):
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
            self._write("appearance/theme", self._theme)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def theme(self):
        return self._theme

    @theme.setter
    def theme(self, val: str):
        val = val.lower()
        if val not in self.VALID_THEMES:
            val = "dark"
        if val != self._theme:
            self._theme = val
            self._dark_mode = val != "light"
            self._write("appearance/theme", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def accentColor(self):
        return self._accent_color

    @accentColor.setter
    def accentColor(self, color: str):
        if color != self._accent_color:
            self._accent_color = color
            self._write("appearance/accent_color", color)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def highContrast(self):
        return self._high_contrast

    @highContrast.setter
    def highContrast(self, val: bool):
        if val != self._high_contrast:
            self._high_contrast = val
            self._write("accessibility/high_contrast", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def compactMode(self):
        return self._compact_mode

    @compactMode.setter
    def compactMode(self, val: bool):
        if val != self._compact_mode:
            self._compact_mode = val
            self._write("appearance/compact_mode", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(str, notify=themeChanged)
    def fontScale(self):
        return self._font_scale

    @fontScale.setter
    def fontScale(self, val: str):
        if val != self._font_scale:
            self._font_scale = val
            self._write("accessibility/font_size", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def reduceMotion(self):
        return self._reduce_motion

    @reduceMotion.setter
    def reduceMotion(self, val: bool):
        if val != self._reduce_motion:
            self._reduce_motion = val
            self._write("accessibility/reduce_motion", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def reduceTransparency(self):
        return self._reduce_transparency

    @reduceTransparency.setter
    def reduceTransparency(self, val: bool):
        if val != self._reduce_transparency:
            self._reduce_transparency = val
            self._write("accessibility/reduce_transparency", val)
            self._notify_theme_store()
            self.themeChanged.emit()

    @Slot(result=dict)
    def themeInfo(self):
        return {
            "theme": self._theme,
            "dark_mode": self._dark_mode,
            "accent_color": self._accent_color,
            "high_contrast": self._high_contrast,
            "reduce_motion": self._reduce_motion,
            "reduce_transparency": self._reduce_transparency,
            "valid_themes": list(self.VALID_THEMES),
        }
