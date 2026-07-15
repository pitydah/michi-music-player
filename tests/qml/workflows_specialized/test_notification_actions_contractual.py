"""MO: Test NotificationBridge — all actions contractual, undo without handler."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.notification_bridge import NotificationBridge


@pytest.fixture
def bridge():
    return NotificationBridge()


@pytest.fixture
def bridge_full():
    return NotificationBridge(
        action_registry=MagicMock(),
        job_bridge=MagicMock(),
        notification_service=MagicMock(),
        navigation_bridge=MagicMock(),
        diagnostics_service=MagicMock(),
    )


@pytest.fixture
def bridge_nav_only():
    return NotificationBridge(
        action_registry=MagicMock(),
        navigation_bridge=MagicMock(),
    )


class TestNotificationActionsContractual:
    def test_show_message_returns_ok(self, bridge):
        result = bridge.showMessage("Test message", "info")
        assert result["ok"] is True

    def test_show_action_returns_ok(self, bridge):
        result = bridge.showAction("Action required", "openJob", "info")
        assert result["ok"] is True

    def test_show_progress_returns_ok(self, bridge):
        result = bridge.showProgress("Working...", "job_1", 50)
        assert result["ok"] is True

    def test_dismiss_clears_current(self, bridge):
        bridge.showMessage("Test", "info")
        assert bridge._current is not None
        bridge.dismiss()
        assert bridge._current is None

    def test_clear_empties_all(self, bridge):
        bridge.showMessage("A", "info")
        bridge.showMessage("B", "info")
        bridge.dismiss()
        bridge.clear()
        assert bridge._current is None
        assert len(bridge._queue) == 0

    def test_execute_current_action_no_notification(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["error"] == "NO_CURRENT_NOTIFICATION"

    def test_execute_current_action_no_action_id(self, bridge):
        bridge.showMessage("No action", "info")
        result = bridge.executeCurrentAction()
        assert result["error"] == "NO_ACTION"

    def test_execute_notification_action_not_found(self, bridge):
        result = bridge.executeNotificationAction("nonexistent")
        assert result["error"] == "NOT_FOUND"

    def test_undo_without_handler_returns_ok(self, bridge):
        result = bridge.undoAction("some_key")
        assert result.get("ok") is True
        assert result.get("undo") == "some_key"

    def test_undo_with_registry_calls_registry(self, bridge_full):
        bridge_full._action_registry.execute.return_value = {"ok": True}
        result = bridge_full.undoAction("test_key")
        bridge_full._action_registry.execute.assert_called_once_with("undo_test_key")
        assert result["ok"] is True

    def test_open_job_without_any_handler(self, bridge):
        result = bridge.openJob("42")
        assert result["error"] == "NO_NAVIGATION_TARGET"

    def test_open_job_with_navigation(self, bridge_nav_only):
        result = bridge_nav_only.openJob("42")
        bridge_nav_only._navigation_bridge.navigate.assert_called_once_with("audio_lab.jobs")
        assert result["ok"] is True

    def test_cancel_job_by_id_without_bridge(self, bridge):
        result = bridge.cancelJobById("42")
        assert result["error"] == "UNSUPPORTED"

    def test_cancel_job_by_id_with_job_bridge(self, bridge_full):
        bridge_full._job_bridge.cancelJob.return_value = {"ok": True}
        result = bridge_full.cancelJobById("42")
        assert result["ok"] is True

    def test_show_track_without_anything(self, bridge):
        result = bridge.showTrack(1)
        assert result["error"] == "NO_ACTION"

    def test_show_track_with_navigation(self, bridge_full):
        result = bridge_full.showTrack(1, album_key="album_abc")
        bridge_full._navigation_bridge.navigateWithParams.assert_called_once_with(
            "library.album_detail", {"album_key": "album_abc"}
        )
        assert result["ok"] is True

    def test_show_device_without_navigation(self, bridge):
        result = bridge.showDevice("device_x")
        assert result["error"] == "NO_NAVIGATION"

    def test_show_device_with_navigation(self, bridge_full):
        result = bridge_full.showDevice("device_x")
        bridge_full._navigation_bridge.navigate.assert_called_once_with("home_audio")
        assert result["ok"] is True

    def test_open_diagnostics_without_navigation(self, bridge):
        result = bridge.openDiagnostics()
        assert result["error"] == "NO_NAVIGATION"

    def test_open_diagnostics_with_navigation(self, bridge_full):
        result = bridge_full.openDiagnostics()
        bridge_full._navigation_bridge.navigate.assert_called_once_with("diagnostics")
        assert result["ok"] is True

    def test_open_settings_without_navigation(self, bridge):
        result = bridge.openSettings()
        assert result["error"] == "NO_NAVIGATION"

    def test_open_settings_with_navigation(self, bridge_full):
        result = bridge_full.openSettings()
        bridge_full._navigation_bridge.navigate.assert_called_once_with("settings.general")
        assert result["ok"] is True

    def test_retry_calls_execute(self, bridge_full):
        bridge_full.showAction("Retry me", "undo", "info")
        nid = bridge_full._current["id"]
        bridge_full._action_registry.execute.return_value = {"ok": True}
        result = bridge_full.executeNotificationAction(nid)
        assert result.get("ok") is True
        bridge_full._action_registry.execute.assert_called_once()

    def test_update_progress_creates_if_missing(self, bridge):
        result = bridge.updateProgress("new_job", 25, "Progress update")
        assert result.get("ok") is True

    def test_update_progress_updates_existing(self, bridge):
        bridge.showProgress("First", "job_a", 10)
        result = bridge.updateProgress("job_a", 50, "Updated")
        assert result.get("ok") is True

    def test_dedup_prevents_duplicate(self, bridge):
        bridge.showMessage("Same message", "info")
        result = bridge.showMessage("Same message", "info")
        assert result.get("dedup") is True

    def test_persistent_notification_stored(self, bridge):
        bridge.showMessage("Persistent error", "error")
        assert len(bridge._persistent_map) > 0

    def test_notification_score(self, bridge):
        score = bridge.notificationScore()
        assert "score" in score
        assert "has_current" in score

    def test_queue_length(self, bridge):
        bridge.showMessage("First", "info")
        bridge.dismiss()
        bridge.showMessage("Second", "info")
        bridge.dismiss()
        bridge.showMessage("Third", "info")
        assert bridge.queueLength == 0

    def test_max_queue_does_not_grow(self, bridge):
        for i in range(30):
            bridge.showMessage(f"Message {i}", "info")
        assert bridge.queueLength <= 20

    def test_execute_action_via_registry(self, bridge_full):
        bridge_full._action_registry.execute.return_value = {"ok": True}
        bridge_full.showAction("Custom", "custom_action", "info")
        result = bridge_full.executeCurrentAction()
        assert result.get("ok") is True
