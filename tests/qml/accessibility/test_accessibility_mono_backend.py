from __future__ import annotations
"""Test AccessibilityBridge — font_scale, high_contrast, reduced_motion,
focus_indicators, mono, balance.

Single authority (S11): the AccessibilityService owns state and persistence;
the bridge is a thin adapter that delegates and applies mono/balance to the
playback backend. Backend rejections revert the QML control."""

from unittest.mock import MagicMock

from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from core.accessibility_service import AccessibilityService
import pytest
pytestmark = [pytest.mark.qml_module("accessibility")]


class _FakeSettings:
    def __init__(self, initial: dict | None = None):
        self._data = dict(initial or {})

    def value(self, key, default=None):
        return self._data.get(key, default)

    def setValue(self, key, value):
        self._data[key] = value


class FakePlaybackService:
    def __init__(self):
        self.mono_enabled = False
        self.balance_value = 0.0

    def set_mono(self, enabled: bool):
        self.mono_enabled = enabled

    def set_balance(self, balance: float):
        self.balance_value = balance


class FakePlaybackServiceUnstable:
    def set_mono(self, enabled: bool):
        raise RuntimeError("Backend mono unavailable")

    def set_balance(self, balance: float):
        raise RuntimeError("Backend balance unavailable")


def _bridge(playback=None, settings=None):
    service = AccessibilityService(settings=settings or _FakeSettings())
    return AccessibilityBridge(service=service, playback_service=playback)


class TestFontScale:
    def test_set_font_scale(self):
        backend = _FakeSettings()
        bridge = _bridge(settings=backend)
        bridge.fontScale = 1.5
        assert bridge.fontScale == 1.5
        assert backend.value("accessibility/font_size") == 1.5

    def test_font_scale_noop_same(self):
        bridge = _bridge()
        bridge.fontScale = 1.0
        assert bridge.fontScale == 1.0


class TestHighContrast:
    def test_set_high_contrast(self):
        backend = _FakeSettings()
        bridge = _bridge(settings=backend)
        bridge.highContrast = True
        assert bridge.highContrast is True
        assert backend.value("accessibility/high_contrast") is True

    def test_high_contrast_toggle_off(self):
        bridge = _bridge()
        bridge.highContrast = True
        bridge.highContrast = False
        assert bridge.highContrast is False


class TestReduceMotion:
    def test_set_reduce_motion(self):
        backend = _FakeSettings()
        bridge = _bridge(settings=backend)
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True
        assert backend.value("accessibility/reduced_motion") is True

    def test_reduce_motion_toggle(self):
        bridge = _bridge()
        bridge.reduceMotion = True
        bridge.reduceMotion = False
        assert bridge.reduceMotion is False


class TestFocusIndicators:
    def test_set_focus_indicators(self):
        backend = _FakeSettings()
        bridge = _bridge(settings=backend)
        bridge.focusIndicators = False
        assert bridge.focusIndicators is False
        assert backend.value("accessibility/focus_indicators") is False


class TestMono:
    def test_mono_setter_sends_to_backend(self):
        ps = FakePlaybackService()
        bridge = _bridge(playback=ps)
        bridge.mono = True
        assert ps.mono_enabled is True
        assert bridge.mono is True

    def test_mono_toggle_off(self):
        ps = FakePlaybackService()
        bridge = _bridge(playback=ps)
        bridge.mono = True
        bridge.mono = False
        assert ps.mono_enabled is False
        assert bridge.mono is False

    def test_mono_restores_on_backend_rejection(self):
        ps = FakePlaybackServiceUnstable()
        bridge = _bridge(playback=ps)
        bridge.mono = True
        assert bridge.mono is False

    def test_mono_no_playback_service(self):
        bridge = _bridge(playback=None)
        old = bridge.mono
        bridge.mono = not old
        assert bridge.mono == old


class TestBalance:
    def test_balance_setter_sends_to_backend(self):
        ps = FakePlaybackService()
        bridge = _bridge(playback=ps)
        bridge.balance = 0.3
        assert ps.balance_value == 0.3
        assert bridge.balance == 0.3

    def test_balance_clamps_values(self):
        ps = FakePlaybackService()
        bridge = _bridge(playback=ps)
        bridge.balance = 5.0
        assert bridge.balance == 1.0
        bridge.balance = -5.0
        assert bridge.balance == -1.0

    def test_balance_restores_on_backend_rejection(self):
        ps = FakePlaybackServiceUnstable()
        bridge = _bridge(playback=ps)
        bridge.balance = 0.5
        assert bridge.balance == 0.0

    def test_balance_no_playback_service(self):
        bridge = _bridge(playback=None)
        bridge.balance = 0.5
        assert bridge.balance == 0.5


class TestRestoreOnError:
    def test_restore_on_error(self):
        bridge = _bridge()
        bridge.balance = 0.3
        result = bridge.restoreOnError()
        assert result["ok"] is True
        assert result["mono"] is False
        assert result["balance"] == 0.0

    def test_restore_emits_signal(self):
        bridge = _bridge()
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
        bridge = _bridge()
        bridge.fontScale = 1.5
        bridge.refresh()
        assert bridge.fontScale is not None

    def test_refresh_emits_signal(self):
        bridge = _bridge()
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
        bridge.mono = True
        assert bridge.lastError != ""

    def test_last_error_on_backend_rejection_balance(self):
        ps = FakePlaybackServiceUnstable()
        bridge = AccessibilityBridge(playback_service=ps)
        bridge.balance = 0.5
        assert bridge.lastError != ""
