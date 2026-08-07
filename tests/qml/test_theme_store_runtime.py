"""Tests for ThemeStore runtime — settings change  ThemeBridge  ThemeService  ThemeStore  QML color update  persistence.

Single authority (S11): the ThemeService owns state and persistence; the
bridge is a thin adapter. Persistence survives service re-instantiation."""
from unittest.mock import MagicMock

import pytest

from core.theme_service import ThemeService
from core.accessibility_service import AccessibilityService
from ui_qml_bridge.theme_bridge import ThemeBridge


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


@pytest.fixture
def bridge():
    b = ThemeBridge(
        service=ThemeService(settings=_FakeSettings()),
        accessibility_service=AccessibilityService(settings=_FakeSettings()),
    )
    return b


class TestThemeBridgeProperties:
    def test_initial_dark_mode(self, bridge):
        assert bridge.darkMode is True
        assert bridge.theme == "dark"

    def test_theme_setter_persists_via_service(self, bridge):
        bridge.theme = "light"
        assert bridge._service.theme == "light"

    def test_theme_setter_updates_dark_mode(self, bridge):
        bridge.theme = "light"
        assert bridge.darkMode is False
        assert bridge.theme == "light"

    def test_accent_color_setter(self, bridge):
        bridge.accentColor = "#FF0000"
        assert bridge.accentColor == "#FF0000"
        assert bridge._service.accent_color == "#FF0000"

    def test_high_contrast_setter(self, bridge):
        bridge.highContrast = True
        assert bridge.highContrast is True

    def test_compact_mode_setter(self, bridge):
        bridge.compactMode = True
        assert bridge.compactMode is True

    def test_font_scale_setter(self, bridge):
        bridge.fontScale = 1.5
        assert bridge.fontScale == 1.5

    def test_reduce_motion_setter(self, bridge):
        bridge.reducedMotion = True
        assert bridge.reducedMotion is True

    def test_theme_setter_emits_signal(self, bridge):
        handler = MagicMock()
        bridge.themeChanged.connect(handler)
        bridge.theme = "light"
        handler.assert_called_once()

    def test_theme_noop_same_value(self, bridge):
        backend = bridge._service._settings
        bridge.theme = "dark"
        assert backend.value("appearance/theme") is None


class TestThemeStoreIntegration:
    def test_theme_store_values_after_update(self):
        class FakeThemeStore:
            def __init__(self):
                self.currentTheme = "dark"
                self.accentColor = "#8FB7FF"
                self.highContrast = False
                self.compactMode = False
                self.fontScale = 1.0
                self.reducedMotion = False
                self.darkMode = True
                self.ready = False

            def updateFromBridge(self, bridge):
                self.currentTheme = bridge.theme
                self.accentColor = bridge.accentColor
                self.highContrast = bridge.highContrast
                self.compactMode = bridge.compactMode
                self.fontScale = bridge.fontScale
                self.reducedMotion = bridge.reducedMotion
                self.darkMode = bridge.darkMode
                self.ready = True

        store = FakeThemeStore()
        backend = _FakeSettings({
            "appearance/theme": "light",
            "appearance/accent_color": "#00FF00",
            "accessibility/high_contrast": True,
            "appearance/compact_mode": True,
            "accessibility/font_size": 1.5,
            "accessibility/reduced_motion": True,
        })
        bridge = ThemeBridge(
            service=ThemeService(settings=backend),
            accessibility_service=AccessibilityService(settings=backend),
        )

        store.updateFromBridge(bridge)

        assert store.currentTheme == "light"
        assert store.accentColor == "#00FF00"
        assert store.highContrast is True
        assert store.compactMode is True
        assert store.fontScale == 1.5
        assert store.reducedMotion is True
        assert store.darkMode is False
        assert store.ready is True

    def test_settings_change_propagates_to_bridge(self, bridge):
        bridge.theme = "light"
        bridge.accentColor = "#FF7A00"
        bridge.highContrast = True

        assert bridge.theme == "light"
        assert bridge.accentColor == "#FF7A00"
        assert bridge.highContrast is True

    def test_persistence_survives_simulated_restart(self):
        backend = _FakeSettings()

        bridge1 = ThemeBridge(
            service=ThemeService(settings=backend),
            accessibility_service=AccessibilityService(settings=backend),
        )
        bridge1.theme = "light"
        bridge1.highContrast = True

        bridge2 = ThemeBridge(
            service=ThemeService(settings=backend),
            accessibility_service=AccessibilityService(settings=backend),
        )
        assert bridge2.theme == "light"
        assert bridge2.highContrast is True
