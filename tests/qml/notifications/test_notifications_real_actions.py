from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.action_registry import ActionRegistry
pytestmark = [pytest.mark.qml_module("notification")]



@pytest.fixture
def action_registry():
    r = ActionRegistry()
    return r


@pytest.fixture
def mock_registry():
    r = MagicMock()
    r.execute.return_value = {"ok": True}
    return r


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    jb.navigateToJob = MagicMock(return_value={"ok": True})
    jb.retryJob = MagicMock(return_value={"ok": True})
    return jb


@pytest.fixture
def bridge(mock_registry, job_bridge):
    return NotificationBridge(
        action_registry=mock_registry,
        job_bridge=job_bridge,
    )


class TestRealActions:
    def test_open_job_navigates_to_jobs(self, bridge, job_bridge):
        result = bridge.openJob("42")
        assert result.get("ok") is True

    def test_open_job_fallback_to_action_registry(self, bridge, mock_registry):
        bridge._job_bridge = None
        bridge.openJob("42")
        mock_registry.execute.assert_called_once_with("navigate_jobs")

    def test_open_job_no_bridge_no_registry(self):
        empty = NotificationBridge()
        result = empty.openJob("42")
        assert result.get("ok") is False

    def test_retry_job(self, bridge, job_bridge):
        result = bridge.retryJob("42")
        assert result.get("ok") is True

    def test_retry_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.retryJob("42")
        assert result.get("ok") is False

    def test_cancel_job_by_id(self, bridge, job_bridge):
        result = bridge.cancelJobById("42")
        assert result.get("ok") is True

    def test_open_diagnostics(self, bridge, mock_registry):
        result = bridge.openDiagnostics()
        assert result.get("ok") is True

    def test_open_diagnostics_no_registry(self):
        empty = NotificationBridge()
        res = empty.openDiagnostics()
        assert res.get("ok") is False

    def test_show_track(self, bridge, mock_registry):
        result = bridge.showTrack(42)
        assert result.get("ok") is True

    def test_show_device(self, bridge, mock_registry):
        result = bridge.showDevice("device_1")
        assert result.get("ok") is True

<<<<<<< Updated upstream
    def test_undo_action(self, bridge, mock_registry):
        result = bridge.undoAction("track_add_to_queue")
=======
<<<<<<< HEAD
    def test_undo_action_no_handler(self, bridge):
        bridge._action_registry = None
        result = bridge.undoAction("track_add_to_queue")
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED_UNDO"
=======
    def test_undo_action(self, bridge, mock_registry):
        result = bridge.undoAction("track_add_to_queue")
>>>>>>> Stashed changes
        assert result.get("ok") is True
        mock_registry.execute.assert_called_once_with("undo_track_add_to_queue")

    def test_undo_action_no_registry(self):
        empty = NotificationBridge()
        result = empty.undoAction("track_add_to_queue")
        assert result.get("ok") is True
        assert result.get("undo") == "track_add_to_queue"
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
