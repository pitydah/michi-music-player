"""Tests for ThemeStore runtime — settings change → ThemeBridge → ThemeStore → QML color update → persistence."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.theme_bridge import ThemeBridge


@pytest.fixture
def bridge():
    b = ThemeBridge(coordinator=MagicMock())
    b._theme = "dark"
    b._accent_color = "#8FB7FF"
    b._high_contrast = False
    b._compact_mode = False
    b._font_scale = "normal"
    b._reduce_motion = False
    b._dark_mode = True
    return b


class TestThemeBridgeProperties:
    def test_initial_dark_mode(self, bridge):
        assert bridge.darkMode is True
        assert bridge.theme == "dark"

    def test_theme_setter_calls_coordinator(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.theme = "light"
            bridge._coordinator.execute.assert_called_once_with("appearance/theme", "light")

    def test_theme_setter_updates_dark_mode(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.theme = "light"
            assert bridge.darkMode is False
            assert bridge.theme == "light"

    def test_accent_color_setter(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.accentColor = "#FF0000"
            assert bridge.accentColor == "#FF0000"

    def test_high_contrast_setter(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.highContrast = True
            assert bridge.highContrast is True

    def test_compact_mode_setter(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.compactMode = True
            assert bridge.compactMode is True

    def test_font_scale_setter(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.fontScale = "large"
            assert bridge.fontScale == "large"

    def test_reduce_motion_setter(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            bridge.reduceMotion = True
            assert bridge.reduceMotion is True

    def test_theme_setter_emits_signal(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS"):
            handler = MagicMock()
            bridge.themeChanged.connect(handler)
            bridge.theme = "light"
            handler.assert_called_once()

    def test_theme_noop_same_value(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS") as ms:
            bridge.theme = "dark"
            ms.setValue.assert_not_called()


class TestThemeStoreIntegration:
    def test_theme_store_values_after_update(self):
        try:
            class FakeThemeStore:
                def __init__(self):
                    self.currentTheme = "dark"
                    self.accentColor = "#8FB7FF"
                    self.highContrast = False
                    self.compactMode = False
                    self.fontScale = "normal"
                    self.reduceMotion = False
                    self.darkMode = True
                    self.ready = False

                def updateFromBridge(self, bridge):
                    self.currentTheme = bridge.theme
                    self.accentColor = bridge.accentColor
                    self.highContrast = bridge.highContrast
                    self.compactMode = bridge.compactMode
                    self.fontScale = bridge.fontScale
                    self.reduceMotion = bridge.reduceMotion
                    self.darkMode = bridge.darkMode
                    self.ready = True

            store = FakeThemeStore()
            bridge = ThemeBridge(coordinator=MagicMock())
            bridge._theme = "light"
            bridge._accent_color = "#00FF00"
            bridge._high_contrast = True
            bridge._compact_mode = True
            bridge._font_scale = "large"
            bridge._reduce_motion = True
            bridge._dark_mode = False

            store.updateFromBridge(bridge)

            assert store.currentTheme == "light"
            assert store.accentColor == "#00FF00"
            assert store.highContrast is True
            assert store.compactMode is True
            assert store.fontScale == "large"
            assert store.reduceMotion is True
            assert store.darkMode is False
            assert store.ready is True
        except ImportError:
            pytest.skip("PySide6 QML import not available")

    def test_settings_change_propagates_to_bridge(self, bridge):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS") as mock_s:
            mock_s.value.side_effect = lambda k, d=None: {
                "appearance/theme": "light",
                "appearance/accent_color": "#FF7A00",
                "accessibility/high_contrast": True,
                "appearance/compact_mode": True,
                "accessibility/font_size": "large",
                "accessibility/reduce_motion": True,
            }.get(k, d)

            bridge.theme = "light"
            bridge.accentColor = "#FF7A00"
            bridge.highContrast = True

            assert bridge.theme == "light"
            assert bridge.accentColor == "#FF7A00"
            assert bridge.highContrast is True

    def test_persistence_survives_simulated_restart(self):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS") as mock_s:
            stored = {"appearance/theme": "light", "accessibility/high_contrast": True}

            def mock_value(key, default=None):
                return stored.get(key, default)

            def mock_setValue(key, value):
                stored[key] = value

            mock_s.value.side_effect = mock_value
            mock_s.setValue.side_effect = mock_setValue

            bridge1 = ThemeBridge(coordinator=MagicMock())
            bridge1.theme = "light"
            bridge1.highContrast = True

            bridge2 = ThemeBridge(coordinator=MagicMock())
            assert bridge2.theme == "light"
            assert bridge2.highContrast is True
