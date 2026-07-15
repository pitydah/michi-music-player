"""Tests for notification action execution."""
from unittest.mock import MagicMock


from ui_qml_bridge.notification_bridge import NotificationBridge


class TestNotificationActions:
    def test_execute_current_action_no_action(self):
        bridge = NotificationBridge()
        bridge.showMessage("Test")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False
        assert result["error"] == "NO_ACTION"

    def test_execute_current_action_with_action(self):
        registry = MagicMock()
        registry.execute.return_value = {"ok": True}
        bridge = NotificationBridge(action_registry=registry)
        bridge.showAction("Test action", "navigate_home")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True
        registry.execute.assert_called_with("navigate_home")

    def test_execute_notification_action_not_found(self):
        bridge = NotificationBridge()
        result = bridge.executeNotificationAction("nonexistent")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_execute_notification_action_by_id(self):
        registry = MagicMock()
        registry.execute.return_value = {"ok": True}
        bridge = NotificationBridge(action_registry=registry)
        bridge.showAction("Test", "navigate_home")
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(nid)
        assert result["ok"] is True

    def test_dismiss_removes_current(self):
        bridge = NotificationBridge()
        bridge.showMessage("Test")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_dismiss_by_id(self):
        bridge = NotificationBridge()
        bridge.showMessage("Test")
        nid = bridge.currentNotification["id"]
        bridge.dismiss(nid)
        assert bridge.currentNotification is None

    def test_clear_removes_all(self):
        bridge = NotificationBridge()
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_action_executed_signal_emitted(self):
        registry = MagicMock()
        registry.execute.return_value = {"ok": True}
        bridge = NotificationBridge(action_registry=registry)
        handler = MagicMock()
        bridge.actionExecuted.connect(handler)
        bridge.showAction("Test", "navigate_home")
        bridge.executeCurrentAction()
        handler.assert_called_once()

    def test_cancel_job_action(self):
        job_bridge = MagicMock()
        job_bridge.cancelJob.return_value = {"ok": True}
        bridge = NotificationBridge(job_bridge=job_bridge)
        result = bridge.cancelJobById("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_with(42)

    def test_retry_action(self):
        bridge = NotificationBridge()
        bridge.showAction("Retry this", "retry")
        result = bridge.retry(bridge.currentNotification["id"])
        assert result["ok"] is False  # No registry

    def test_show_message_kinds(self):
        bridge = NotificationBridge()
        for kind in ("info", "success", "warning", "error"):
            result = bridge.showMessage(kind + " test", kind=kind)
            assert result["ok"] is True

    def test_queue_max_size(self):
        bridge = NotificationBridge()
        bridge._max_queue = 3
        for i in range(10):
            bridge.showMessage("Msg " + str(i))
        assert len(bridge._queue) <= 3
