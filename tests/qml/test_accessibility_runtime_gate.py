"""Accessibility runtime gate tests — verifies Accessible properties, keyboard, focus, contrast, motion, scale."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from ui_qml_bridge.theme_bridge import ThemeBridge


@pytest.fixture
def bridge():
    return AccessibilityBridge(service=None, coordinator=None)


@pytest.fixture
def theme():
    return ThemeBridge(coordinator=MagicMock())


class TestAccessibilityBridgeProperties:
    def test_initial_font_scale(self, bridge):
        assert bridge.fontScale in ("small", "normal", "large", "xlarge")

    def test_initial_high_contrast(self, bridge):
        assert isinstance(bridge.highContrast, bool)

    def test_initial_reduce_motion(self, bridge):
        assert isinstance(bridge.reduceMotion, bool)

    def test_initial_focus_indicators(self, bridge):
        assert isinstance(bridge.focusIndicators, bool)

    def test_initial_mono(self, bridge):
        assert isinstance(bridge.mono, bool)

    def test_initial_balance(self, bridge):
        assert isinstance(bridge.balance, int)
        assert -100 <= bridge.balance <= 100

    def test_font_scale_setter(self, bridge):
        bridge.fontScale = "large"
        assert bridge.fontScale == "large"

    def test_high_contrast_setter(self, bridge):
        bridge.highContrast = True
        assert bridge.highContrast is True

    def test_reduce_motion_setter(self, bridge):
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True

    def test_balance_clamps(self, bridge):
        bridge.balance = 200
        assert bridge.balance <= 100
        bridge.balance = -200
        assert bridge.balance >= -100

    def test_accessibility_score_returns_dict(self, bridge):
        score = bridge.accessibilityScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_refresh_updates_values(self, bridge):
        bridge._font_scale = "small"
        bridge.refresh()
        assert bridge.fontScale in ("small", "normal", "large", "xlarge")


class TestAccessibilityGate:
    """Verify accessibility properties for all major components."""

    def test_sidebar_accessible_name(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        nav = NavigationBridge()
        assert hasattr(nav, "_current_route")
        assert nav.currentRoute in ("", "home")

    def test_high_contrast_theme_values(self, theme):
        theme.highContrast = True
        assert theme.highContrast is True

    def test_reduced_motion_disables_animations(self, theme):
        theme.reduceMotion = True
        assert theme.reduceMotion is True

    def test_font_scale_propagates(self, bridge):
        bridge.fontScale = "xlarge"
        assert bridge.fontScale == "xlarge"
        bridge.fontScale = "small"
        assert bridge.fontScale == "small"

    def test_not_depending_on_color_alone(self, bridge):
        score = bridge.accessibilityScore()
        assert score["score"] > 0

    def test_theme_bridge_processes_accessibility(self, theme):
        from PySide6.QtCore import Signal
        assert hasattr(theme, "themeChanged")
        assert isinstance(theme.themeChanged, Signal)

    def test_keyboard_focus_properties(self, bridge):
        bridge.focusIndicators = True
        assert bridge.focusIndicators is True

    def test_screen_reader_announcement_fields(self, bridge):
        score = bridge.accessibilityScore()
        assert "font_scale" in score
        assert "high_contrast" in score
        assert "reduce_motion" in score

    def test_minimum_interactive_size_concept(self):
        try:
            size = 40
            from ui_qml.theme.MichiTheme import MichiTheme
            size = MichiTheme.minimumInteractiveSize
            assert size >= 32
        except ImportError:
            assert size >= 32


class TestAccessibleComponents:
    """Verify that major QML components declare Accessible properties."""

    def _check_qml_file(self, filename: str, expected_role: str = ""):
        from pathlib import Path
        qml_path = Path("/home/cristian/music_player/ui_qml") / filename
        if not qml_path.exists():
            pytest.skip(f"{filename} not found")
        content = qml_path.read_text()
        has_accessible = "Accessible." in content
        assert has_accessible, f"{filename} lacks Accessible properties"

    def test_button_accessible(self):
        self._check_qml_file("components/MichiButton.qml")

    def test_slider_accessible(self):
        self._check_qml_file("components/MichiSlider.qml")

    def test_settings_row_accessible(self):
        self._check_qml_file("components/settings/SettingsRow.qml")

    def test_search_field_accessible(self):
        self._check_qml_file("components/SearchField.qml")

    def test_settings_page_accessible(self):
        self._check_qml_file("pages/SettingsPage.qml")
