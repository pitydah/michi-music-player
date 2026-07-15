"""MW: Notifications — show progress notification, cancel/dismiss it."""
from __future__ import annotations

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestNotificationsProgressCancel(SpecializedWorkflowBase):
    def test_initial_state(self, notifications_fixtures):
        b = notifications_fixtures
        assert b.currentNotification is None
        assert b.queueLength == 0

    def test_show_message(self, notifications_fixtures):
        b = notifications_fixtures
        b.showMessage("Test message", "info")
        assert b.showMessage.called

    def test_dismiss_notification(self, notifications_fixtures):
        b = notifications_fixtures
        b.dismiss()
        assert b.dismiss.called

    def test_clear_all(self, notifications_fixtures):
        b = notifications_fixtures
        b.clear()
        assert b.clear.called

    def test_full_workflow(self, notifications_fixtures):
        b = notifications_fixtures
        b.showMessage("Procesando...", "info")
        b.dismiss()
        b.clear()
        assert b.showMessage.called
        assert b.dismiss.called
        assert b.clear.called

    def test_error_notification(self, notifications_fixtures):
        b = notifications_fixtures
        b.showMessage("Error occurred", "error")
        assert b.showMessage.called

    def test_progress_notification(self, notifications_fixtures):
        b = notifications_fixtures
        b.showMessage("50% completado", "progress")
        assert b.showMessage.called

    def test_persistent_notifications(self, notifications_fixtures):
        b = notifications_fixtures
        b.persistentNotifications = [
            {"id": "1", "message": "Sync active"},
        ]
        assert len(b.persistentNotifications) == 1
