"""Workflow test: show progress  open center  click cancel  verify job state via NotificationBridge."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.notification_bridge import NotificationBridge

pytestmark = [pytest.mark.qml_module("notifications"), pytest.mark.qml_workflow("notifications")]


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    jb.navigateToJob.return_value = {"ok": True}
    return jb


@pytest.fixture
def action_registry():
    ar = MagicMock()
    ar.execute.return_value = {"ok": True}
    return ar


@pytest.fixture
def bridge(job_bridge, action_registry):
    nb = NotificationBridge(job_bridge=job_bridge, action_registry=action_registry)
    nb._next = MagicMock(wraps=nb._next)
    return nb


class TestNotificationsWorkflow:
    """Complete workflow: show progress  open center  click cancel  verify job state."""

    def test_wf_show_toast(self, bridge):
        result = bridge.showMessage("Biblioteca actualizada", "success")
        assert result["ok"] is True
        assert bridge.currentNotification is not None
        assert bridge.currentNotification["text"] == "Biblioteca actualizada"
        assert bridge.currentNotification["kind"] == "success"

    def test_wf_toast_dismiss(self, bridge):
        bridge.showMessage("Dismiss me")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_wf_toast_auto_queue(self, bridge):
        bridge.showMessage("First")
        bridge.dismiss()
        bridge.showMessage("Second")
        bridge.showMessage("Third")
        assert bridge.currentNotification is not None
        assert bridge.queueLength == 1

    def test_wf_toast_queue_drain(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.showMessage("D")
        bridge.dismiss()
        assert bridge.currentNotification is not None or bridge.queueLength <= 3

    def test_wf_clear_all(self, bridge):
        bridge.showMessage("Msg 1")
        bridge.showMessage("Msg 2")
        bridge.showMessage("Msg 3")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_wf_notification_open_center(self, bridge):
        bridge.showMessage("Centro de notificaciones")
        assert bridge.currentNotification is not None

    def test_wf_notification_center_open_close(self, bridge):
        bridge.showMessage("Notificación 1")
        bridge.showMessage("Notificación 2")
        bridge.dismiss()
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_wf_progress_notification(self, bridge):
        result = bridge.showProgress("Descargando...", "job_1", 25)
        assert result["ok"] is True
        assert bridge.currentNotification is not None
        assert bridge.currentNotification["progress"] == 25
        assert bridge.currentNotification["job_id"] == "job_1"

    def test_wf_progress_update(self, bridge):
        bridge.showProgress("Iniciando...", "job_progress", 0)
        result = bridge.updateProgress("job_progress", 0.5, "50% completado")
        assert result["ok"] is True
        assert bridge.currentNotification["progress"] == 50
        assert bridge.currentNotification["text"] == "50% completado"

    def test_wf_progress_complete(self, bridge):
        bridge.showProgress("Procesando...", "job_complete", 0)
        bridge.updateProgress("job_complete", 1.0, "Completado")
        assert bridge.currentNotification["progress"] == 100

    def test_wf_progress_multiple_jobs(self, bridge):
        bridge.showProgress("Job A", "job_a", 10)
        bridge.showProgress("Job B", "job_b", 50)
        assert bridge.currentNotification is not None

    def test_wf_cancel_by_action(self, bridge, job_bridge):
        bridge.showProgress("Transfiriendo...", "42", 50)
        bridge.executeNotificationAction("42")
        assert job_bridge.cancelJob.called

    def test_wf_cancel_by_id(self, bridge, job_bridge):
        bridge.showProgress("Trabajo en curso", "42", 50)
        result = bridge.cancelJobById("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(42)

    def test_wf_cancel_no_such_job(self, bridge, job_bridge):
        job_bridge.cancelJob.side_effect = ValueError("Not found")
        result = bridge.cancelJobById("999")
        assert result["ok"] is False

    def test_wf_cancel_then_verify(self, bridge, job_bridge):
        bridge.showProgress("Sync...", "sync_1", 30)
        result = bridge.cancelJobById("sync_1")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(1)

    def test_wf_dismiss_during_progress(self, bridge):
        bridge.showProgress("Don't cancel", "keep_job", 50)
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_wf_progress_then_message(self, bridge):
        bridge.showProgress("Working...", "job_mix", 50)
        bridge.dismiss()
        bridge.showMessage("Done", "success")
        assert bridge.currentNotification["text"] == "Done"

    def test_wf_execute_current_action(self, bridge, action_registry):
        bridge.showAction("Abrir", "navigate_library")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True
        action_registry.execute.assert_called_once_with("navigate_library")

    def test_wf_execute_action_without_action(self, bridge):
        bridge.showMessage("No action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_wf_execute_action_none_notification(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_wf_dismiss_persistent(self, bridge):
        bridge.showMessage("Persistent error", "error", persistent=True)
        assert bridge.currentNotification is not None
        bridge.dismiss(bridge.currentNotification["id"])
        assert bridge.currentNotification is None

    def test_wf_action_without_job_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.cancelJobById("42")
        assert result["ok"] is False

    def test_wf_notification_score(self, bridge):
        score = bridge.notificationScore()
        assert score["score"] > 0
        assert score["has_action_registry"] is True
        assert score["has_job_bridge"] is True
        assert score["has_current"] is False

    def test_wf_score_after_notification(self, bridge):
        bridge.showMessage("Score test")
        score = bridge.notificationScore()
        assert score["has_current"] is True
        assert score["queue_length"] == 0

    def test_wf_full_workflow(self, bridge, job_bridge):
        bridge.showMessage("Inicio de proceso", "info")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        bridge.showProgress("Sincronizando...", "sync_main", 10)
        assert bridge.currentNotification["progress"] == 10
        bridge.updateProgress("sync_main", 0.5, "Mitad del camino")
        assert bridge.currentNotification["progress"] == 50
        bridge.updateProgress("sync_main", 1.0, "Completado")
        assert bridge.currentNotification["progress"] == 100
        bridge.dismiss()
        bridge.showMessage("Proceso completado", "success")
        assert bridge.currentNotification["kind"] == "success"
        bridge.clear()
        assert bridge.currentNotification is None
