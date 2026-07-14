from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.accessibility_bridge import AccessibilityBridge


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
        raise RuntimeError("Backend unavailable")

    def set_balance(self, balance: int):
        raise RuntimeError("Backend unavailable")


class TestMonoBalance:
    @pytest.fixture
    def settings_service(self):
        svc = MagicMock()
        svc.set_.return_value = {"ok": True}
        return svc

    @pytest.fixture
    def coordinator(self):
        c = MagicMock()
        c.execute.return_value = {"ok": True}
        return c

    def test_mono_setter_sends_to_backend(self, settings_service, coordinator):
        ps = FakePlaybackService()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._mono = False
        bridge.mono = True
        assert ps.mono_enabled is True
        assert bridge.mono is True

    def test_mono_toggle_off(self, settings_service, coordinator):
        ps = FakePlaybackService()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._mono = True
        bridge.mono = False
        assert ps.mono_enabled is False
        assert bridge.mono is False

    def test_mono_restores_on_backend_rejection(self, settings_service, coordinator):
        ps = FakePlaybackServiceUnstable()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._mono = False
        bridge.mono = True
        assert bridge.mono is False

    def test_balance_setter_sends_to_backend(self, settings_service, coordinator):
        ps = FakePlaybackService()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._balance = 0
        bridge.balance = 30
        assert ps.balance_value == 30
        assert bridge.balance == 30

    def test_balance_clamps_values(self, settings_service, coordinator):
        ps = FakePlaybackService()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._balance = 0
        bridge.balance = 150
        assert bridge.balance == 100
        bridge.balance = -200
        assert bridge.balance == -100

    def test_balance_restores_on_backend_rejection(self, settings_service, coordinator):
        ps = FakePlaybackServiceUnstable()
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator,
                                     playback_service=ps)
        bridge._balance = 0
        bridge.balance = 50
        assert bridge.balance == 0

    def test_mono_no_playback_service(self, settings_service, coordinator):
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator)
        old = bridge.mono
        bridge.mono = not old
        assert bridge.mono == old

    def test_balance_no_playback_service(self, settings_service, coordinator):
        bridge = AccessibilityBridge(settings_service=settings_service,
                                     settings_coordinator=coordinator)
        old = bridge.balance
        bridge.balance = 50
        assert bridge.balance == old
