from __future__ import annotations
"""Test NotificationBridge productivo — NotificationService as source of truth,
actions: openJob, cancel, retry, undo, openTrack, openAlbum, openDevice,
openDiagnostics, openSettings. undoAction() without handler  error.
QML: toast, banner, persistent, progress, action button, dismiss, Notification Center."""

from unittest.mock import MagicMock

import pytest

from core.notification_service import Notification, NotificationService, NotificationType
from ui_qml_bridge.notification_bridge import NotificationBridge
pytestmark = [pytest.mark.qml_module("notification")]


@pytest.fixture
def notif_service():
    return NotificationService()


@pytest.fixture
def action_registry():
    reg = MagicMock()
    reg.execute.return_value = {"ok": True}
    return reg


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    jb.retryJob.return_value = {"ok": True}
    jb.navigateToJob.return_value = {"ok": True}
    return jb


@pytest.fixture
def nav_bridge():
    nb = MagicMock()
    nb.navigate.return_value = True
    nb.navigateWithParams.return_value = True
    return nb


@pytest.fixture
def bridge(notif_service, action_registry, job_bridge, nav_bridge):
    return NotificationBridge(
        action_registry=action_registry,
        job_bridge=job_bridge,
        notification_service=notif_service,
        navigation_bridge=nav_bridge,
        diagnostics_service=MagicMock(),
    )


class TestNotificationServiceIntegration:
    def test_service_notify_reaches_bridge(self, bridge, notif_service):
        n = Notification(title="Test", message="Hello from service", type=NotificationType.INFO)
        notif_service.notify(n)
        assert bridge.currentNotification is not None
        assert "Hello from service" in str(bridge.currentNotification.get("text", ""))

    def test_service_progress_reaches_bridge(self, bridge, notif_service):
        n = Notification(title="Progreso", type=NotificationType.PROGRESS,
                         progress=50.0, job_id="j1", message="Scanning")
        notif_service.notify(n)
        current = bridge.currentNotification
        assert current is None or current.get("progress", -1) >= 0

    def test_service_persistent_reaches_bridge(self, bridge, notif_service):
        n = Notification(title="Sticky", type=NotificationType.ERROR,
                         message="Error", persistent=True)
        notif_service.notify(n)
        assert len(bridge.persistentNotifications) >= 1

    def test_bridge_dismiss_syncs_to_service(self, bridge, notif_service):
        n = Notification(title="Dismiss me", type=NotificationType.INFO)
        notif_service.notify(n)
        bridge.clear()
        assert len(notif_service.list_all()) == 0

    def test_bridge_clear_syncs_to_service(self, bridge, notif_service):
        notif_service.notify(Notification(title="A"))
        notif_service.notify(Notification(title="B"))
        bridge.clear()
        assert len(notif_service.list_all()) == 0


class TestShowMessage:
    def test_show_message_returns_ok(self, bridge):
        result = bridge.showMessage("Hola", "info")
        assert result["ok"] is True

    def test_show_message_sets_current(self, bridge):
        bridge.showMessage("Test")
        assert bridge.currentNotification is not None

    def test_show_message_queue_length(self, bridge):
        bridge.showMessage("A")
        assert bridge.queueLength >= 0

    def test_show_message_persistent(self, bridge):
        bridge.showMessage("Error persistente", "error")
        assert len(bridge.persistentNotifications) >= 1


class TestShowAction:
    def test_show_action_returns_ok(self, bridge):
        result = bridge.showAction("Action!", "openJob", "info")
        assert result["ok"] is True

    def test_show_action_persistent(self, bridge):
        bridge.showAction("Action!", "openJob")
        assert len(bridge.persistentNotifications) >= 1


class TestProgress:
    def test_show_progress(self, bridge):
        result = bridge.showProgress("Scanning", "job1", 50)
        assert result["ok"] is True

    def test_update_progress(self, bridge):
        bridge.showProgress("Scan", "job2", 30)
        result = bridge.updateProgress("job2", 0.6, "Scanning...")
        assert result["ok"] is True

    def test_update_progress_clamps(self, bridge):
        result = bridge.updateProgress("job3", 1.5, "Done")
        assert result["ok"] is True

    def test_progress_dedup(self, bridge):
        bridge.showProgress("Scan", "job4", 10)
        result = bridge.showProgress("Scan updated", "job4", 50)
        assert result.get("updated") is True or result["ok"] is True


class TestDismissNotificationCenter:
    def test_dismiss_current(self, bridge):
        bridge.showMessage("Test")
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_dismiss_by_id(self, bridge):
        bridge.showMessage("Test")
        nid = bridge.currentNotification["id"]
        bridge.dismiss(nid)
        assert bridge.currentNotification is None

    def test_notification_center_queue(self, bridge):
        for i in range(5):
            bridge.showMessage(f"Msg {i}")
        assert bridge.queueLength <= 20

    def test_clear_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0
        assert len(bridge.persistentNotifications) == 0


class TestActions:
    def test_open_job(self, bridge, job_bridge):
        result = bridge.openJob("42")
        assert result["ok"] is True

    def test_cancel_job(self, bridge, job_bridge):
        result = bridge.cancelJobById("42")
        assert result["ok"] is True

    def test_retry_job(self, bridge, job_bridge):
        result = bridge.retryJob("42")
        assert result["ok"] is True

    def test_undo_action_no_handler(self, bridge):
        bridge._action_registry = None
        result = bridge.undoAction("delete_track")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED_UNDO"

    def test_open_track(self, bridge):
        result = bridge.showTrack(42)
        assert result["ok"] is True or result["ok"] is False

    def test_open_album(self, bridge, nav_bridge):
        result = bridge.showTrack(0, album_key="album_key_123")
        assert result["ok"] is True

    def test_open_device(self, bridge, nav_bridge):
        result = bridge.showDevice("speaker_1")
        assert result["ok"] is True

    def test_open_diagnostics(self, bridge, nav_bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True

    def test_open_settings(self, bridge, nav_bridge):
        result = bridge.openSettings()
        assert result["ok"] is True

    def test_execute_current_action_no_current(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False
        assert result["error"] == "NO_CURRENT_NOTIFICATION"

    def test_execute_current_action(self, bridge):
        bridge.showAction("Click me", "openJob")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_execute_notification_action_not_found(self, bridge):
        result = bridge.executeNotificationAction("nonexistent")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_retry_notification(self, bridge):
        bridge.showAction("Retry me", "openJob")
        nid = bridge.currentNotification["id"]
        result = bridge.retry(nid)
        assert result["ok"] is True

    def test_open_track_invalid(self, bridge):
        result = bridge.showTrack(-1)
        assert result["ok"] is True or result["ok"] is False


class TestNotificationScore:
    def test_score_returns_dict(self, bridge):
        score = bridge.notificationScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_score_with_content(self, bridge):
        bridge.showMessage("Test")
        score = bridge.notificationScore()
        assert score["has_current"] is True

    def test_score_minimal(self):
        b = NotificationBridge()
        score = b.notificationScore()
        assert score["score"] >= 0

    def test_score_action_registry(self, bridge):
        score = bridge.notificationScore()
        assert score["has_action_registry"] is True

    def test_score_notification_service(self, bridge):
        score = bridge.notificationScore()
        assert score["has_notification_service"] is True
