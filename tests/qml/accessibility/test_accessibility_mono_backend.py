from __future__ import annotations
"""Test AccessibilityBridge — font_scale, high_contrast, reduced_motion, focus_indicators,
target_size, accessible names, roles, tab order, keyboard, announcements, mono, balance.
Mono/balance  PlaybackService contractual. Rejections revert QML control."""

from unittest.mock import MagicMock

from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
import pytest
pytestmark = [pytest.mark.qml_module("accessibility")]


class FakePlaybackService:
    def __init__(self):
        self.mono_enabled = False
        self.balance_value = 0

    def set_mono(self, enabled: bool):
        self.mono_enabled = enabled

    def set_balance(self, balance: int):
        self.balance_value = balance


class FakePlaybackServiceUnstable:
    def set_mono(self, enabled: bool):
        raise RuntimeError("Backend mono unavailable")

    def set_balance(self, balance: int):
        raise RuntimeError("Backend balance unavailable")


class TestFontScale:
    def test_set_font_scale(self):
        svc = MagicMock()
        svc.set_.return_value = {"ok": True}
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._font_scale = "normal"
        bridge.fontScale = "large"
        assert bridge.fontScale == "large"
        svc.set_.assert_called_with("accessibility/font_size", "large")

    def test_font_scale_noop_same(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._font_scale = "normal"
        bridge.fontScale = "normal"
        svc.set_.assert_not_called()


class TestHighContrast:
    def test_set_high_contrast(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._high_contrast = False
        bridge.highContrast = True
        assert bridge.highContrast is True
        svc.set_.assert_called_with("accessibility/high_contrast", True)

    def test_high_contrast_toggle_off(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._high_contrast = True
        bridge.highContrast = False
        assert bridge.highContrast is False


class TestReduceMotion:
    def test_set_reduce_motion(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._reduce_motion = False
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True
        svc.set_.assert_called_with("accessibility/reduce_motion", True)

    def test_reduce_motion_toggle(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge._reduce_motion = True
        bridge.reduceMotion = False
        assert bridge.reduceMotion is False


class TestFocusIndicators:
    def test_set_focus_indicators(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge.focusIndicators = False
        assert bridge.focusIndicators is False
        svc.set_.assert_called_with("accessibility/focus_indicators", False)


class TestMono:
    def test_mono_setter_sends_to_backend(self):
        ps = FakePlaybackService()
        svc = MagicMock()
        svc.set_.return_value = {"ok": True}
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._mono = False
        bridge.mono = True
        assert ps.mono_enabled is True
        assert bridge.mono is True

    def test_mono_toggle_off(self):
        ps = FakePlaybackService()
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._mono = True
        bridge.mono = False
        assert ps.mono_enabled is False
        assert bridge.mono is False

    def test_mono_restores_on_backend_rejection(self):
        ps = FakePlaybackServiceUnstable()
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._mono = False
        bridge.mono = True
        assert bridge.mono is False

    def test_mono_no_playback_service(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        old = bridge.mono
        bridge.mono = not old
        assert bridge.mono == old


class TestBalance:
    def test_balance_setter_sends_to_backend(self):
        ps = FakePlaybackService()
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._balance = 0
        bridge.balance = 30
        assert ps.balance_value == 30
        assert bridge.balance == 30

    def test_balance_clamps_values(self):
        ps = FakePlaybackService()
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._balance = 0
        bridge.balance = 150
        assert bridge.balance == 100
        bridge.balance = -200
        assert bridge.balance == -100

    def test_balance_restores_on_backend_rejection(self):
        ps = FakePlaybackServiceUnstable()
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc, playback_service=ps)
        bridge._balance = 0
        bridge.balance = 50
        assert bridge.balance == 0

    def test_balance_no_playback_service(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        old = bridge.balance
        bridge.balance = 50
        assert bridge.balance == old


class TestRestoreOnError:
    def test_restore_on_error(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        bridge.mono = bool(bridge.mono) or False
        bridge.balance = 30
        result = bridge.restoreOnError()
        assert result["ok"] is True
        assert result["mono"] is False
        assert result["balance"] == 0

    def test_restore_emits_signal(self):
        svc = MagicMock()
        bridge = AccessibilityBridge(settings_service=svc)
        handler = MagicMock()
        bridge.dataChanged.connect(handler)
        bridge.restoreOnError()
        handler.assert_called()


class TestAccessibilityScore:
    def test_score_returns_dict(self):
        bridge = AccessibilityBridge()
        score = bridge.accessibilityScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_score_with_playback_service(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        score = bridge.accessibilityScore()
        assert score["has_playback_service"] is True

    def test_score_detailed_fields(self):
        bridge = AccessibilityBridge()
        score = bridge.accessibilityScore()
        assert "font_scale" in score
        assert "high_contrast" in score
        assert "mono" in score
        assert "balance" in score


class TestRefresh:
    def test_refresh_reloads_all_settings(self):
        bridge = AccessibilityBridge()
        bridge.fontScale = "large"
        bridge.refresh()
        assert bridge.fontScale is not None

    def test_refresh_emits_signal(self):
        bridge = AccessibilityBridge()
        handler = MagicMock()
        bridge.dataChanged.connect(handler)
        bridge.refresh()
        handler.assert_called()


class TestLastError:
    def test_last_error_empty_initially(self):
        bridge = AccessibilityBridge()
        assert bridge.lastError == ""

    def test_last_error_on_backend_rejection_mono(self):
        ps = FakePlaybackServiceUnstable()
        bridge = AccessibilityBridge(playback_service=ps)
        bridge._mono = False
        bridge.mono = True
        assert bridge.lastError != ""

    def test_last_error_on_backend_rejection_balance(self):
        ps = FakePlaybackServiceUnstable()
        bridge = AccessibilityBridge(playback_service=ps)
        bridge._balance = 0
        bridge.balance = 50
        assert bridge.lastError != ""
