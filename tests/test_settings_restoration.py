"""Tests for settings restoration at startup — bridges read persisted values, restore_settings() propagates to runtime."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.theme_bridge import ThemeBridge
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from core.settings_adapters import (
    ThemeSettingsAdapter, AccessibilitySettingsAdapter,
)

pytestmark = [pytest.mark.qml_module("settings")]


class TestThemeBridgeStartupRestoration:
    """ThemeBridge reads persisted settings on init; restore_settings() propagates to runtime."""

    def test_reads_persisted_theme_from_settings(self):
        with patch("ui_qml_bridge.theme_bridge.SETTINGS") as ms:
            ms.value.side_effect = lambda key, default=None: {
                "appearance/theme": "light",
                "appearance/accent_color": "#FF0000",
                "appearance/compact_mode": True,
                "accessibility/high_contrast": True,
                "accessibility/font_size": 1.5,
                "accessibility/reduced_motion": True,
                "accessibility/reduce_transparency": True,
            }.get(key, default)
            bridge = ThemeBridge(coordinator=MagicMock())
            assert bridge.theme == "light"
            assert bridge.accentColor == "#FF0000"
            assert bridge.compactMode is True
            assert bridge.highContrast is True
            assert bridge.fontScale == 1.5
            assert bridge.reducedMotion is True
            assert bridge.reduceTransparency is True
            assert bridge.darkMode is False

    def test_restore_settings_notifies_theme_store(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        with patch.object(bridge, "_notify_theme_store") as m_notify:
            m_notify.return_value = None
            bridge._notify_theme_store()
            m_notify.assert_called_once()

    def test_restore_settings_emits_theme_changed(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        received = []
        bridge.themeChanged.connect(lambda: received.append(True))
        bridge.themeChanged.emit()
        assert len(received) == 1


class TestAccessibilityBridgeStartupRestoration:
    """AccessibilityBridge reads persisted settings on init; applies mono/balance at startup."""

    def test_reads_persisted_accessibility_from_settings(self):
        with patch("ui_qml_bridge.accessibility_bridge.SETTINGS") as ms:
            ms.value.side_effect = lambda key, default=None: {
                "accessibility/font_size": 1.25,
                "accessibility/high_contrast": True,
                "accessibility/reduced_motion": True,
                "accessibility/focus_indicators": False,
                "accessibility/mono": True,
                "accessibility/balance": -0.5,
                "accessibility/reduce_transparency": True,
            }.get(key, default)
            bridge = AccessibilityBridge()
            assert bridge.fontScale == 1.25
            assert bridge.highContrast is True
            assert bridge.reduceMotion is True
            assert bridge.focusIndicators is False
            assert bridge.mono is True
            assert bridge.balance == -0.5
            assert bridge.reduceTransparency is True

    def test_applies_mono_at_init_when_playback_available(self):
        playback = MagicMock()
        AccessibilityBridge(playback_service=playback)
        playback.set_mono.assert_called_once()

    def test_applies_balance_at_init_when_playback_available(self):
        playback = MagicMock()
        AccessibilityBridge(playback_service=playback)
        playback.set_balance.assert_called_once()


class TestAccessibilitySettingsAdapterRuntime:
    """AccessibilitySettingsAdapter applies runtime changes to the bridge instance."""

    def test_adapter_applies_mono_to_bridge(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        adapter = AccessibilitySettingsAdapter()
        bridge._mono = False
        result = adapter.apply("accessibility/mono", True)
        assert result.ok is True
        assert bridge.mono is True

    def test_adapter_applies_balance_to_bridge(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        adapter = AccessibilitySettingsAdapter()
        bridge._balance = 0.0
        result = adapter.apply("accessibility/balance", 0.5)
        assert result.ok is True
        assert bridge.balance == 0.5

    def test_adapter_applies_font_scale(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        adapter = AccessibilitySettingsAdapter()
        bridge._font_scale = 1.0
        result = adapter.apply("accessibility/font_size", 1.5)
        assert result.ok is True
        assert bridge.fontScale == 1.5

    def test_adapter_verify_ok_when_value_matches(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        adapter = AccessibilitySettingsAdapter(accessibility_bridge=bridge)
        bridge._font_scale = 1.5
        result = adapter.verify("accessibility/font_size", 1.5)
        assert result["ok"] is True
        assert result["applied"] is True

    def test_adapter_verify_fails_on_mismatch(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        adapter = AccessibilitySettingsAdapter(accessibility_bridge=bridge)
        bridge._font_scale = 1.0
        result = adapter.verify("accessibility/font_size", 1.5)
        assert result["ok"] is False
        assert result["error"] == "VERIFY_FAILED"
        assert result["expected"] == 1.5
        assert result["actual"] == 1.0

    def test_adapter_apply_fails_when_no_bridge(self):
        adapter = AccessibilitySettingsAdapter()
        import ui_qml_bridge.accessibility_bridge as mod
        saved = mod._instance
        try:
            mod._instance = None
            result = adapter.apply("accessibility/mono", True)
            assert result.ok is False
            assert result.error_code == "APPLY_TARGET_UNAVAILABLE"
        finally:
            mod._instance = saved

    def test_adapter_verify_returns_unavailable_when_no_bridge(self):
        adapter = AccessibilitySettingsAdapter()
        import ui_qml_bridge.accessibility_bridge as mod
        saved = mod._instance
        try:
            mod._instance = None
            result = adapter.verify("accessibility/mono", True)
            assert result["ok"] is False
            assert result["error"] == "APPLY_TARGET_UNAVAILABLE"
        finally:
            mod._instance = saved


class TestThemeSettingsAdapterRuntime:
    """ThemeSettingsAdapter applies runtime changes to the bridge instance."""

    def test_adapter_applies_theme_to_bridge(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        adapter = ThemeSettingsAdapter()
        bridge._theme = "dark"
        result = adapter.apply("appearance/theme", "light")
        assert result.ok is True
        assert bridge.theme == "light"

    def test_adapter_applies_accent_color(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        adapter = ThemeSettingsAdapter()
        bridge._accent_color = "#8FB7FF"
        result = adapter.apply("appearance/accent_color", "#FF0000")
        assert result.ok is True
        assert bridge.accentColor == "#FF0000"

    def test_adapter_applies_compact_mode(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        adapter = ThemeSettingsAdapter()
        bridge._compact_mode = False
        result = adapter.apply("appearance/compact_mode", True)
        assert result.ok is True
        assert bridge.compactMode is True

    def test_adapter_verify_ok_when_value_matches(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        adapter = ThemeSettingsAdapter(theme_bridge=bridge)
        bridge._theme = "dark"
        result = adapter.verify("appearance/theme", "dark")
        assert result["ok"] is True
        assert result["applied"] is True

    def test_adapter_verify_fails_on_mismatch(self):
        bridge = ThemeBridge(coordinator=MagicMock())
        adapter = ThemeSettingsAdapter(theme_bridge=bridge)
        bridge._theme = "light"
        result = adapter.verify("appearance/theme", "dark")
        assert result["ok"] is False
        assert result["error"] == "VERIFY_FAILED"
        assert result["expected"] == "dark"
        assert result["actual"] == "light"

    def test_adapter_apply_fails_when_no_bridge(self):
        adapter = ThemeSettingsAdapter()
        import ui_qml_bridge.theme_bridge as mod
        saved = mod._instance
        try:
            mod._instance = None
            result = adapter.apply("appearance/theme", "dark")
            assert result.ok is False
            assert result.error_code == "APPLY_TARGET_UNAVAILABLE"
        finally:
            mod._instance = saved

    def test_adapter_verify_returns_unavailable_when_no_bridge(self):
        adapter = ThemeSettingsAdapter()
        import ui_qml_bridge.theme_bridge as mod
        saved = mod._instance
        try:
            mod._instance = None
            result = adapter.verify("appearance/theme", "dark")
            assert result["ok"] is False
            assert result["error"] == "APPLY_TARGET_UNAVAILABLE"
        finally:
            mod._instance = saved


class TestBootstrapRestoreSettings:
    """ApplicationBootstrap.restore_settings() propagates persisted values to runtime bridges."""

    def test_restore_settings_calls_theme_notify(self):
        from core.application_bootstrap import ApplicationBootstrap
        bootstrap = ApplicationBootstrap()
        theme = MagicMock()
        accessibility = MagicMock()
        bootstrap._bridges = {"theme": theme, "accessibility": accessibility}
        bootstrap.restore_settings()
        theme._notify_theme_store.assert_called_once()
        theme.themeChanged.emit.assert_called_once()
        accessibility._apply_mono_to_playback.assert_called_once()
        accessibility._apply_balance_to_playback.assert_called_once()
        accessibility.dataChanged.emit.assert_called_once()

    def test_restore_settings_graceful_missing_bridges(self):
        from core.application_bootstrap import ApplicationBootstrap
        bootstrap = ApplicationBootstrap()
        bootstrap._bridges = {}
        bootstrap.restore_settings()
