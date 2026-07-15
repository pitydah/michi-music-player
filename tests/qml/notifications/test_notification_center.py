
import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge


@pytest.fixture
def bridge():
    return NotificationBridge()


class TestNotificationCenter:

    def test_queue_length_starts_zero(self, bridge):
        assert bridge.queueLength == 0

    def test_queue_increases_after_showing(self, bridge):
        bridge.showMessage("First")
        assert bridge.queueLength == 0
        bridge.showMessage("Second")
        assert bridge.queueLength == 1

    def test_dismiss_removes_current_and_pulls_from_queue(self, bridge):
        bridge.showMessage("First")
        bridge.showMessage("Second")
        bridge.dismiss()
        assert bridge.currentNotification["text"] == "Second"
        assert bridge.queueLength == 0

    def test_multiple_dismiss_drains_queue(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.dismiss()
        bridge.dismiss()
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_persistent_notifications_appear_in_map(self, bridge):
        bridge.showMessage("Error test", "error")
        assert len(bridge._persistent_map) == 1

    def test_persistent_map_cleared_on_dismiss(self, bridge):
        bridge.showMessage("Error test", "error")
        nid = bridge.currentNotification["id"]
        assert nid in bridge._persistent_map
        bridge.dismiss()
        assert nid not in bridge._persistent_map


class TestDismissAll:
    def test_clear_removes_all(self, bridge):
        bridge.showMessage("A")
        bridge.showMessage("B")
        bridge.showMessage("C")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0
        assert len(bridge._persistent_map) == 0

    def test_clear_removes_persistent_too(self, bridge):
        bridge.showMessage("Persistent", "error")
        bridge.showMessage("Normal")
        bridge.clear()
        assert bridge.currentNotification is None
        assert len(bridge._persistent_map) == 0

    def test_clear_does_not_crash_on_empty(self, bridge):
        bridge.clear()
        assert bridge.currentNotification is None


class TestEmptyState:
    def test_empty_initially(self, bridge):
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_empty_after_full_drain(self, bridge):
        bridge.showMessage("Temp")
        bridge.dismiss()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_empty_notification_score(self, bridge):
        score = bridge.notificationScore()
        assert score["has_current"] is False
        assert score["queue_length"] == 0
