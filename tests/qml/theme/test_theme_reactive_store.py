from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.theme_bridge import ThemeBridge
pytestmark = [pytest.mark.qml_module("theme")]



class TestThemeReactiveStore:
    @pytest.fixture
    def settings_service(self):
        svc = MagicMock()
        svc.set_.return_value = {"ok": True}
        return svc

    def test_theme_change_persists_via_service(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._theme = "dark"
        bridge.theme = "light"
        settings_service.set_.assert_called_with("appearance/theme", "light")

    def test_theme_setter_updates_state(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._theme = "dark"
        bridge.theme = "light"
        assert bridge.theme == "light"
        assert bridge.darkMode is False

    def test_theme_noop_on_same_value(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._theme = "dark"
        bridge.theme = "dark"
        settings_service.set_.assert_not_called()

    def test_accent_color_persists(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._accent_color = "#8FB7FF"
        bridge.accentColor = "#FF0000"
        assert bridge.accentColor == "#FF0000"
        settings_service.set_.assert_called()

    def test_high_contrast_emits_signal(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        handler = MagicMock()
        bridge.themeChanged.connect(handler)
        bridge._high_contrast = False
        bridge.highContrast = True
        handler.assert_called_once()

    def test_compact_mode_via_service(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._compact_mode = False
        bridge.compactMode = True
        settings_service.set_.assert_called_with("appearance/compact_mode", True)

    def test_reduce_motion_propagates(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._reduce_motion = False
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True
        settings_service.set_.assert_called_with("accessibility/reduce_motion", True)

    def test_notify_theme_store_does_not_crash(self, settings_service):
        bridge = ThemeBridge(service=settings_service)
        bridge._notify_theme_store()

    def test_no_service_no_fallback(self):
        bridge = ThemeBridge(service=None)
        bridge._theme = "dark"
        bridge.theme = "light"
        assert bridge.theme == "light"
