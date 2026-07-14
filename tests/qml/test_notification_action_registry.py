"""Test NotificationBridge — ActionRegistry integration with action_id, primary/secondary action,
progress, cancel, update, retry, dismiss, error persistence, accessibility.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.action_registry import ActionRegistry


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
    return jb


@pytest.fixture
def bridge(mock_registry, job_bridge):
    return NotificationBridge(
        action_registry=mock_registry,
        job_bridge=job_bridge,
    )


class TestActionIntegration:
    def test_action_id_present(self, bridge):
        bridge.showAction("Test action", "navigate_home")
        n = bridge.currentNotification
        assert n is not None
        assert n.get("action") == "navigate_home"

    def test_primary_action_executes(self, bridge, mock_registry):
        bridge.showAction("Primary", "playback_playpause")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True
        mock_registry.execute.assert_called_with("playback_playpause")

    def test_execute_notification_action_returns_result(self, bridge, mock_registry):
        bridge.showAction("Test", "library_refresh")
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(str(nid))
        assert result["ok"] is True

    def test_progress_tracking(self, bridge):
        bridge.showProgress("Working...", "job_1", 30)
        n = bridge.currentNotification
        assert n is not None
        assert n["progress"] == 30
        assert n["job_id"] == "job_1"

    def test_progress_update(self, bridge):
        bridge.showProgress("Start", "job_upd", 0)
        result = bridge.updateProgress("job_upd", 0.5, "Halfway")
        assert result["ok"] is True
        n = bridge.currentNotification
        assert n is not None
        assert n["progress"] == 50

    def test_progress_update_float(self, bridge):
        bridge.showProgress("Start", "job_flt", 0)
        result = bridge.updateProgress("job_flt", 0.75)
        assert result["ok"] is True

    def test_cancel_job(self, bridge, job_bridge):
        bridge.showProgress("Job running", "42", 50)
        result = bridge.cancelJob("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_with(42)

    def test_retry_action(self, bridge, mock_registry):
        bridge.showAction("Retry test", "retry_action")
        nid = bridge.currentNotification["id"]
        result = bridge.retry(str(nid))
        assert result["ok"] is True
        assert mock_registry.execute.call_count >= 1

    def test_retry_not_found(self, bridge):
        result = bridge.retry("99999")
        assert result["ok"] is False

    def test_retry_limit(self, bridge, mock_registry):
        mock_registry.execute.return_value = {"ok": False, "error": "FAILED"}
        bridge.showAction("Fail", "fail_action")
        nid = bridge.currentNotification["id"]
        r1 = bridge.retry(str(nid))
        assert r1.get("ok") is False or not r1.get("ok")
        r2 = bridge.retry(str(nid))
        assert r2.get("ok") is False or not r2.get("ok")

    def test_dismiss(self, bridge):
        bridge.showMessage("Dismiss me")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_dismiss_queue(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        bridge.dismiss()
        assert bridge.currentNotification is not None

    def test_clear_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_error_persistence(self, bridge, mock_registry):
        mock_registry.execute.return_value = {"ok": False, "error": "PERSIST_ERR"}
        bridge.showAction("Error test", "error_action")
        nid = bridge.currentNotification["id"]
        result = bridge.retry(str(nid))
        assert result.get("ok") is False

    def test_accessibility_announcement(self, bridge):
        bridge.showMessage("Test accessibility")
        assert bridge.currentNotification is not None


class TestScore:
    def test_score_positive(self, bridge):
        score = bridge.notificationScore()
        assert score["score"] > 0

    def test_score_no_registry(self):
        empty = NotificationBridge()
        score = empty.notificationScore()
        assert score["has_action_registry"] is False
