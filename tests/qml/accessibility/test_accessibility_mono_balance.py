from __future__ import annotations

import pytest

from core.accessibility_service import AccessibilityService
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
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
        raise RuntimeError("Backend unavailable")

    def set_balance(self, balance: float):
        raise RuntimeError("Backend unavailable")


class TestMonoBalance:
    @pytest.fixture
    def service(self):
        return AccessibilityService(settings=_FakeSettings())

    def _bridge(self, service, playback=None):
        return AccessibilityBridge(service=service, playback_service=playback)

    def test_mono_setter_sends_to_backend(self, service):
        ps = FakePlaybackService()
        bridge = self._bridge(service, ps)
        bridge.mono = True
        assert ps.mono_enabled is True
        assert bridge.mono is True

    def test_mono_toggle_off(self, service):
        ps = FakePlaybackService()
        bridge = self._bridge(service, ps)
        bridge.mono = True
        bridge.mono = False
        assert ps.mono_enabled is False
        assert bridge.mono is False

    def test_mono_restores_on_backend_rejection(self, service):
        ps = FakePlaybackServiceUnstable()
        bridge = self._bridge(service, ps)
        bridge.mono = True
        assert bridge.mono is False

    def test_balance_setter_sends_to_backend(self, service):
        ps = FakePlaybackService()
        bridge = self._bridge(service, ps)
        bridge.balance = 0.3
        assert ps.balance_value == 0.3
        assert bridge.balance == 0.3

    def test_balance_clamps_values(self, service):
        ps = FakePlaybackService()
        bridge = self._bridge(service, ps)
        bridge.balance = 5.0
        assert bridge.balance == 1.0
        bridge.balance = -5.0
        assert bridge.balance == -1.0

    def test_balance_restores_on_backend_rejection(self, service):
        ps = FakePlaybackServiceUnstable()
        bridge = self._bridge(service, ps)
        bridge.balance = 0.5
        assert bridge.balance == 0.0

    def test_mono_no_playback_service(self, service):
        bridge = self._bridge(service)
        old = bridge.mono
        bridge.mono = not old
        assert bridge.mono == old

    def test_balance_no_playback_service(self, service):
        bridge = self._bridge(service)
        bridge.balance = 0.5
        assert bridge.balance == 0.5
