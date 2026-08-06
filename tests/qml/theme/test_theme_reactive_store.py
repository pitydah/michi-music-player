from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.theme_service import ThemeService
from core.accessibility_service import AccessibilityService
from ui_qml_bridge.theme_bridge import ThemeBridge
pytestmark = [pytest.mark.qml_module("theme")]


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class TestThemeReactiveStore:
    @pytest.fixture
    def theme_service(self):
        return ThemeService(settings=_FakeSettings())

    @pytest.fixture
    def a11y_service(self):
        return AccessibilityService(settings=_FakeSettings())

    @pytest.fixture
    def bridge(self, theme_service, a11y_service):
        return ThemeBridge(service=theme_service, accessibility_service=a11y_service)

    def test_theme_change_persists_via_service(self, theme_service, bridge):
        bridge.theme = "light"
        assert theme_service.theme == "light"
        assert theme_service._read("appearance/theme", "dark") == "light"

    def test_theme_setter_updates_state(self, bridge):
        bridge.theme = "light"
        assert bridge.theme == "light"
        assert bridge.darkMode is False

    def test_theme_noop_on_same_value(self, theme_service, bridge):
        theme_service.set_theme("dark")
        bridge.theme = "dark"
        assert theme_service._read("appearance/theme", "dark") == "dark"

    def test_accent_color_persists(self, theme_service, bridge):
        bridge.accentColor = "#FF0000"
        assert bridge.accentColor == "#FF0000"
        assert theme_service._read("appearance/accent_color", "") == "#FF0000"

    def test_high_contrast_emits_signal(self, a11y_service, bridge):
        handler = MagicMock()
        bridge.highContrastChanged.connect(handler)
        a11y_service.set_high_contrast(True)
        handler.assert_called_once()

    def test_compact_mode_via_service(self, theme_service, bridge):
        bridge.compactMode = True
        assert theme_service.compact_mode is True
        assert theme_service._read("appearance/compact_mode", False) is True

    def test_reduce_motion_propagates(self, a11y_service, bridge):
        bridge.reducedMotion = True
        assert bridge.reducedMotion is True
        assert a11y_service._read("accessibility/reduced_motion", False) is True

    def test_notify_theme_store_does_not_crash(self, bridge):
        bridge._notify_theme_store()

    def test_no_service_no_fallback(self):
        bridge = ThemeBridge(service=None)
        bridge.theme = "light"
        assert bridge.theme == "dark"  # degraded: setters are no-ops
