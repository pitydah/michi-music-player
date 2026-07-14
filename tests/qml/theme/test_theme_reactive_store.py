from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.theme_bridge import ThemeBridge


class TestThemeReactiveStore:
    @pytest.fixture
    def settings_service(self):
        svc = MagicMock()
        def mock_get(key, default=None):
            return default
        svc.get.side_effect = mock_get
        svc.set_.return_value = {"ok": True}
        return svc

    @pytest.fixture
    def coordinator(self):
        c = MagicMock()
        c.execute.return_value = {"ok": True}
        return c

    def test_theme_change_persists_via_service(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge.theme = "light"
        settings_service.set_.assert_called_with("appearance/theme", "light")

    def test_theme_setter_updates_state(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge._theme = "dark"
        bridge.theme = "light"
        assert bridge.theme == "light"
        assert bridge.darkMode is False

    def test_theme_noop_on_same_value(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge._theme = "dark"
        bridge.theme = "dark"
        settings_service.set_.assert_not_called()

    def test_accent_color_skips_if_service_rejects(self, settings_service):
        coordinator = MagicMock()
        coordinator.execute.return_value = {"ok": False}
        settings_service.set_.return_value = {"ok": False}
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge._accent_color = "#8FB7FF"
        old = bridge.accentColor
        bridge.accentColor = "#FF0000"
        assert bridge.accentColor == old

    def test_high_contrast_emits_signal(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        handler = MagicMock()
        bridge.themeChanged.connect(handler)
        bridge.highContrast = True
        handler.assert_called_once()

    def test_compact_mode_via_coordinator_fallback(self, coordinator):
        bridge = ThemeBridge(coordinator=coordinator)
        bridge.compactMode = True
        coordinator.execute.assert_called_with("appearance/compact_mode", True)

    def test_reduce_motion_propagates(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True
        settings_service.set_.assert_called_with("accessibility/reduce_motion", True)

    def test_notify_theme_store_does_not_crash(self, settings_service, coordinator):
        bridge = ThemeBridge(settings_service=settings_service, coordinator=coordinator)
        bridge.notify_theme_store()
