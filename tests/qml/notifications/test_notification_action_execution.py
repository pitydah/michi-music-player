"""Test notification action execution — bridge callback, job cancel, retry."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.action_registry import ActionRegistry


@pytest.fixture
def action_registry():
    ar = MagicMock(spec=ActionRegistry)
    ar.execute.return_value = {"ok": True}
    return ar


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    jb.retryJob.return_value = {"ok": True}
    jb.navigateToJob = MagicMock(return_value={"ok": True})
    return jb


@pytest.fixture
def bridge(action_registry, job_bridge):
    return NotificationBridge(
        action_registry=action_registry,
        job_bridge=job_bridge,
    )


class TestActionButtonExecution:
    def test_action_button_calls_execute_on_registry(self, bridge, action_registry):
        bridge.showAction("Test action", "navigate_home")
        bridge.executeCurrentAction()
        action_registry.execute.assert_called_once_with("navigate_home")

    def test_action_button_returns_ok(self, bridge):
        bridge.showAction("Config", "navigate_settings")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_button_no_current_returns_error(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_action_button_no_action_id_returns_error(self, bridge):
        bridge.showMessage("No action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_action_executed_signal_emitted(self, bridge, action_registry):
        signals = []
        bridge.actionExecuted.connect(lambda a_id, r: signals.append((a_id, r)))
        bridge.showAction("Signal test", "navigate_home")
        bridge.executeCurrentAction()
        assert len(signals) == 1
        assert signals[0][0] == "navigate_home"
        assert signals[0][1]["ok"] is True


class TestJobActions:
    def test_cancel_job_calls_job_bridge(self, bridge, job_bridge):
        bridge.showProgress("Trabajo en curso", "42", 50)
        result = bridge.cancelJobById("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(42)

    def test_cancel_job_missing_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.cancelJobById("42")
        assert result["ok"] is False

    def test_retry_job_calls_bridge(self, bridge, job_bridge):
        result = bridge.retryJob("42")
        assert result["ok"] is True
        job_bridge.retryJob.assert_called_once_with("42")

    def test_retry_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.retryJob("42")
        assert result["ok"] is False


class TestActionByNotificationId:
    def test_execute_by_id_from_persistent(self, bridge, action_registry):
        bridge.showAction("Persistent action", "library_refresh")
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(str(nid))
        assert result["ok"] is True
        action_registry.execute.assert_called_once_with("library_refresh")

    def test_execute_by_id_not_found(self, bridge):
        result = bridge.executeNotificationAction("99999")
        assert result["ok"] is False

    def test_execute_by_id_moves_from_queue(self, bridge, action_registry):
        bridge.showMessage("First")
        bridge.showAction("Second actionable", "playback_playpause")
        bridge.dismiss()
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(str(nid))
        assert result["ok"] is True


class TestOpenTrackAction:
    def test_open_track_with_valid_id(self, bridge, action_registry):
        bridge.showTrack(42)
        action_registry.execute.assert_called_once_with("track_open_album")

    def test_open_track_with_album_key(self, bridge):
        nb = MagicMock()
        bridge._navigation_bridge = nb
        result = bridge.showTrack(0, album_key="album_xyz")
        assert result["ok"] is True
        nb.navigateWithParams.assert_called_once()


class TestOpenDeviceAction:
    def test_open_device(self, bridge):
        nb = MagicMock()
        bridge._navigation_bridge = nb
        result = bridge.showDevice("device_1")
        assert result["ok"] is True
        nb.navigate.assert_called_once_with("home_audio")

    def test_open_device_no_nav(self, bridge, action_registry):
        bridge.showDevice("device_1")
        action_registry.execute.assert_called_once_with("navigate_home_audio")
