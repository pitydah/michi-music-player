"""Tests for Notifications v12 — NotificationBridge with ActionRegistry."""
from unittest.mock import MagicMock, patch

import pytest


class TestNotificationBridgeCreation:
    def test_creation(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        assert nb is not None

    def test_current_default(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        assert nb.currentNotification is None

    def test_queue_length_default(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        assert nb.queueLength == 0

    def test_persistent_default(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        assert len(nb.persistentNotifications) == 0


class TestNotificationOperations:
    def test_show_message(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.showMessage("Hello", kind="info")
        assert result.get("ok")

    def test_show_action(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge(action_registry=MagicMock())
        result = nb.showAction("Click me", "navigate_home")
        assert result.get("ok")

    def test_show_progress(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.showProgress("Loading...", "job_1", 50)
        assert result.get("ok")

    def test_dismiss(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.dismiss()
        assert result.get("ok")

    def test_clear(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        nb.clear()
        assert nb.currentNotification is None

    def test_execute_current_action_no_current(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.executeCurrentAction()
        assert not result.get("ok")

    def test_execute_notification_action_not_found(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.executeNotificationAction("nonexistent")
        assert not result.get("ok")

    def test_score(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        score = nb.notificationScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_open_diagnostics(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        nb = NotificationBridge(navigation_bridge=nav)
        result = nb.openDiagnostics()
        assert result.get("ok")

    def test_open_settings(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        nb = NotificationBridge(navigation_bridge=nav)
        result = nb.openSettings()
        assert result.get("ok")

    def test_open_job(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        nb = NotificationBridge(navigation_bridge=nav)
        result = nb.openJob("job_1")
        assert isinstance(result, dict)

    def test_update_progress(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        result = nb.updateProgress("job_1", 0.5, "Processing...")
        assert result.get("ok")
