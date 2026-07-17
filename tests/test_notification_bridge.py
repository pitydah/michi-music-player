from unittest.mock import MagicMock
from ui_qml_bridge.notification_bridge import NotificationBridge


class TestNotificationBridge:
    def test_create(self):
        bridge = NotificationBridge(notification_service=MagicMock())
        assert bridge is not None
