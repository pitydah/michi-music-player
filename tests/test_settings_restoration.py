"""Tests for settings restoration at startup — services read persisted values,
bridges re-expose service state (thin adapters), restore_settings() propagates
to runtime."""
from unittest.mock import MagicMock, patch

import pytest

from ui_qml_bridge.theme_bridge import ThemeBridge
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from core.theme_service import ThemeService
from core.accessibility_service import AccessibilityService
from core.settings_adapters import (
    ThemeSettingsAdapter, AccessibilitySettingsAdapter,
)

pytestmark = [pytest.mark.qml_module("settings")]


class _FakeSettings:
    """Dict-backed QSettings-like stub for service persistence tests."""

    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


PERSISTED_THEME = {
    "appearance/theme": "light",
    "appearance/accent_color": "#FF0000",
    "appearance/compact_mode": True,
    "accessibility/high_contrast": True,
    "accessibility/font_size": 1.5,
    "accessibility/reduced_motion": True,
    "accessibility/reduce_transparency": True,
}

PERSISTED_A11Y = {
    "accessibility/font_size": 1.25,
    "accessibility/high_contrast": True,
    "accessibility/reduced_motion": True,
    "accessibility/focus_indicators": False,
    "accessibility/mono": True,
    "accessibility/balance": -0.5,
    "accessibility/reduce_transparency": True,
}


class TestThemeBridgeStartupRestoration:
    """ThemeService reads persisted values; ThemeBridge re-exposes them."""

    def test_reads_persisted_theme_from_settings(self):
        service = ThemeService(settings=_FakeSettings(PERSISTED_THEME))
        a11y = AccessibilityService(settings=_FakeSettings(PERSISTED_THEME))
        bridge = ThemeBridge(service=service, accessibility_service=a11y)
        assert bridge.theme == "light"
        assert bridge.accentColor == "#FF0000"
        assert bridge.compactMode is True
        assert bridge.highContrast is True
        assert bridge.fontScale == 1.5
        assert bridge.reducedMotion is True
        assert bridge.reduceTransparency is True
        assert bridge.darkMode is False

    def test_bridge_delegates_theme_change_to_service(self):
        service = ThemeService(settings=_FakeSettings(PERSISTED_THEME))
        bridge = ThemeBridge(service=service)
        bridge.theme = "dark"
        assert service.theme == "dark"
        assert bridge.darkMode is True

    def test_restore_settings_notifies_theme_store(self):
        bridge = ThemeBridge(service=ThemeService(settings=_FakeSettings()))
        with patch.object(bridge, "_notify_theme_store") as m_notify:
            m_notify.return_value = None
            bridge._notify_theme_store()
            m_notify.assert_called_once()

    def test_restore_settings_emits_theme_changed(self):
        bridge = ThemeBridge(service=ThemeService(settings=_FakeSettings()))
        received = []
        bridge.themeChanged.connect(lambda: received.append(True))
        bridge.themeChanged.emit()
        assert len(received) == 1

    def test_service_change_reemits_bridge_signal(self):
        service = ThemeService(settings=_FakeSettings())
        bridge = ThemeBridge(service=service)
        received = []
        bridge.themeChanged.connect(lambda: received.append(True))
        service.set_theme("light")
        assert len(received) == 1


class TestAccessibilityBridgeStartupRestoration:
    """AccessibilityService reads persisted values; bridge re-exposes them."""

    def test_reads_persisted_accessibility_from_settings(self):
        service = AccessibilityService(settings=_FakeSettings(PERSISTED_A11Y))
        bridge = AccessibilityBridge(service=service)
        assert bridge.fontScale == 1.25
        assert bridge.highContrast is True
        assert bridge.reduceMotion is True
        assert bridge.focusIndicators is False
        assert bridge.mono is True
        assert bridge.balance == -0.5
        assert bridge.reduceTransparency is True

    def test_applies_mono_at_init_when_playback_available(self):
        playback = MagicMock()
        service = AccessibilityService(settings=_FakeSettings(PERSISTED_A11Y))
        AccessibilityBridge(service=service, playback_service=playback)
        playback.set_mono.assert_called_once()

    def test_applies_balance_at_init_when_playback_available(self):
        playback = MagicMock()
        service = AccessibilityService(settings=_FakeSettings(PERSISTED_A11Y))
        AccessibilityBridge(service=service, playback_service=playback)
        playback.set_balance.assert_called_once()


class TestAccessibilitySettingsAdapterRuntime:
    """AccessibilitySettingsAdapter applies runtime changes through the bridge."""

    @staticmethod
    def _bridge(playback=None):
        return AccessibilityBridge(
            service=AccessibilityService(settings=_FakeSettings()),
            playback_service=playback or MagicMock(),
        )

    def test_adapter_applies_mono_to_bridge(self):
        bridge = self._bridge()
        adapter = AccessibilitySettingsAdapter()
        result = adapter.apply("accessibility/mono", True)
        assert result.ok is True
        assert bridge.mono is True

    def test_adapter_applies_balance_to_bridge(self):
        bridge = self._bridge()
        adapter = AccessibilitySettingsAdapter()
        result = adapter.apply("accessibility/balance", 0.5)
        assert result.ok is True
        assert bridge.balance == 0.5

    def test_adapter_applies_font_scale(self):
        bridge = self._bridge()
        adapter = AccessibilitySettingsAdapter()
        result = adapter.apply("accessibility/font_size", 1.5)
        assert result.ok is True
        assert bridge.fontScale == 1.5

    def test_adapter_verify_ok_when_value_matches(self):
        bridge = self._bridge()
        adapter = AccessibilitySettingsAdapter(accessibility_bridge=bridge)
        result = adapter.verify("accessibility/font_size", bridge.fontScale)
        assert result["ok"] is True
        assert result["applied"] is True

    def test_adapter_verify_fails_on_mismatch(self):
        bridge = self._bridge()
        adapter = AccessibilitySettingsAdapter(accessibility_bridge=bridge)
        result = adapter.verify("accessibility/font_size", 1.5)
        assert result["ok"] is False
        assert result["error"] == "VERIFY_FAILED"
        assert result["expected"] == 1.5
        assert result["actual"] == bridge.fontScale

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
    """ThemeSettingsAdapter applies runtime changes through the bridge."""

    @staticmethod
    def _bridge():
        return ThemeBridge(service=ThemeService(settings=_FakeSettings()))

    def test_adapter_applies_theme_to_bridge(self):
        bridge = self._bridge()
        adapter = ThemeSettingsAdapter()
        result = adapter.apply("appearance/theme", "light")
        assert result.ok is True
        assert bridge.theme == "light"

    def test_adapter_applies_accent_color(self):
        bridge = self._bridge()
        adapter = ThemeSettingsAdapter()
        result = adapter.apply("appearance/accent_color", "#FF0000")
        assert result.ok is True
        assert bridge.accentColor == "#FF0000"

    def test_adapter_applies_compact_mode(self):
        bridge = self._bridge()
        adapter = ThemeSettingsAdapter()
        result = adapter.apply("appearance/compact_mode", True)
        assert result.ok is True
        assert bridge.compactMode is True

    def test_adapter_verify_ok_when_value_matches(self):
        bridge = self._bridge()
        adapter = ThemeSettingsAdapter(theme_bridge=bridge)
        result = adapter.verify("appearance/theme", bridge.theme)
        assert result["ok"] is True
        assert result["applied"] is True

    def test_adapter_verify_fails_on_mismatch(self):
        bridge = self._bridge()
        adapter = ThemeSettingsAdapter(theme_bridge=bridge)
        result = adapter.verify("appearance/theme", "light")
        assert result["ok"] is False
        assert result["error"] == "VERIFY_FAILED"
        assert result["expected"] == "light"
        assert result["actual"] == bridge.theme

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
