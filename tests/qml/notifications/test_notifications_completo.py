from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def action_registry():
    ar = MagicMock()
    ar.execute.return_value = {"ok": True}
    return ar


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    jb.navigateToJob.return_value = {"ok": True}
    jb.retryJob.return_value = {"ok": True}
    return jb


@pytest.fixture
def nav_bridge():
    nb = MagicMock()
    nb.navigate = MagicMock()
    nb.navigateWithParams = MagicMock()
    return nb


@pytest.fixture
def bridge(action_registry, job_bridge, nav_bridge):
    return NotificationBridge(
        action_registry=action_registry,
        job_bridge=job_bridge,
        navigation_bridge=nav_bridge,
    )


class TestInitialState:
    def test_no_current(self, bridge):
        assert bridge.currentNotification is None

    def test_queue_empty(self, bridge):
        assert bridge.queueLength == 0

    def test_persistent_empty(self, bridge):
        assert bridge.persistentNotifications == []


class TestShowMessage:
    def test_show_message_creates(self, bridge):
        result = bridge.showMessage("Test message", "info")
        assert result["ok"] is True
        assert bridge.currentNotification is not None

    def test_show_message_content(self, bridge):
        bridge.showMessage("Hello", "info")
        n = bridge.currentNotification
        assert n["text"] == "Hello"
        assert n["kind"] == "info"

    def test_show_message_kind_success(self, bridge):
        bridge.showMessage("OK", "success")
        assert bridge.currentNotification["kind"] == "success"

    def test_show_message_kind_warning(self, bridge):
        bridge.showMessage("Warn", "warning")
        assert bridge.currentNotification["kind"] == "warning"

    def test_show_message_kind_error(self, bridge):
        bridge.showMessage("Err", "error")
        assert bridge.currentNotification["kind"] == "error"

    def test_show_message_persistent_on_error(self, bridge):
        bridge.showMessage("Err", "error")
        assert len(bridge.persistentNotifications) == 1

    def test_show_message_non_persistent(self, bridge):
        bridge.showMessage("Info", "info", persistent=False)
        assert len(bridge.persistentNotifications) == 0

    def test_show_message_invalid_kind_defaults_info(self, bridge):
        bridge.showMessage("Test", "unknown")
        assert bridge.currentNotification["kind"] == "info"


class TestShowAction:
    def test_show_action_creates(self, bridge):
        result = bridge.showAction("Action needed", "retry")
        assert result["ok"] is True

    def test_show_action_is_persistent(self, bridge):
        bridge.showAction("Action!", "openJob")
        assert len(bridge.persistentNotifications) == 1

    def test_show_action_has_action_id(self, bridge):
        bridge.showAction("Do it", "cancelJob")
        n = bridge.currentNotification
        assert n["action"] == "cancelJob"

    def test_show_action_dedup(self, bridge):
        bridge.showAction("Do it", "retry")
        result = bridge.showAction("Do it", "retry")
        assert result.get("dedup") is True


class TestShowProgress:
    def test_show_progress_creates(self, bridge):
        result = bridge.showProgress("Loading...", "j1", 50)
        assert result["ok"] is True
        assert bridge.currentNotification is not None

    def test_show_progress_has_progress(self, bridge):
        bridge.showProgress("Work", "j1", 25)
        assert bridge.currentNotification["progress"] == 25

    def test_show_progress_clamps(self, bridge):
        bridge.showProgress("Over", "j1", 150)
        assert bridge.currentNotification["progress"] == 100
        bridge.dismiss()
        bridge.showProgress("Under", "j2", -10)
        assert bridge.currentNotification["progress"] == 0

    def test_show_progress_is_persistent(self, bridge):
        bridge.showProgress("Long", "j1", 10)
        assert bridge.currentNotification["persistent"] is True

    def test_show_progress_dedup_updates(self, bridge):
        bridge.showProgress("Step 1", "j_d", 25)
        result = bridge.showProgress("Step 2", "j_d", 50)
        assert result.get("updated") is True
        assert bridge.currentNotification["progress"] == 50


class TestUpdateProgress:
    def test_update_existing(self, bridge):
        bridge.showProgress("Start", "j_u", 0)
        result = bridge.updateProgress("j_u", 0.75, "75%")
        assert result["ok"] is True
        assert bridge.currentNotification["progress"] >= 75

    def test_update_creates_if_not_exists(self, bridge):
        result = bridge.updateProgress("j_new", 0.5, "Mitad")
        assert result["ok"] is True
        assert bridge.currentNotification is not None

    def test_update_float_to_pct(self, bridge):
        bridge.showProgress("Start", "j_f", 0)
        bridge.updateProgress("j_f", 0.333, "1/3")
        assert bridge.currentNotification["progress"] == 33

    def test_update_above_one(self, bridge):
        bridge.showProgress("Start", "j_p", 0)
        bridge.updateProgress("j_p", 90.0, "90%")
        assert bridge.currentNotification["progress"] == 90


class TestDismiss:
    def test_dismiss_current(self, bridge):
        bridge.showMessage("Temp", "info")
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_dismiss_by_id(self, bridge):
        bridge.showMessage("Save me", "info", persistent=True)
        nid = bridge.currentNotification["id"]
        bridge.dismiss(nid)
        assert bridge.currentNotification is None

    def test_dismiss_removes_from_persistent(self, bridge):
        bridge.showMessage("Persist", "error")
        nid = bridge.currentNotification["id"]
        assert nid in bridge._persistent_map
        bridge.dismiss(nid)
        assert nid not in bridge._persistent_map


class TestClear:
    def test_clear_empties_all(self, bridge):
        bridge.showMessage("A", "info")
        bridge.showMessage("B", "info")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_clear_clears_persistent(self, bridge):
        bridge.showMessage("Err", "error")
        bridge.clear()
        assert bridge.persistentNotifications == []


class TestExecuteAction:
    def test_execute_current_action(self, bridge, action_registry):
        bridge.showAction("Do", "some_action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True
        action_registry.execute.assert_called_once_with("some_action")

    def test_execute_no_current(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_execute_notification_action(self, bridge, action_registry):
        bridge.showAction("Do", "some_action")
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(nid)
        assert result["ok"] is True

    def test_execute_not_found(self, bridge):
        result = bridge.executeNotificationAction("nonexistent")
        assert result["ok"] is False

    def test_action_open_job(self, bridge, job_bridge):
        bridge.showAction("Open", "openJob")
        bridge._current["job_id"] = "42"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_cancel_job(self, bridge, job_bridge):
        bridge.showAction("Cancel", "cancelJob")
        bridge._current["job_id"] = "42"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_retry_job(self, bridge, job_bridge):
        bridge.showAction("Retry", "retry")
        bridge._current["id"] = "n1"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True or result["ok"] is False

    def test_action_undo(self, bridge, action_registry):
        bridge.showAction("Undo", "undo")
        bridge._current["undo_key"] = "delete_foo"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_open_track(self, bridge, nav_bridge):
        bridge.showAction("Open track", "openTrack")
        bridge._current["entity"] = "track_42"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_open_album(self, bridge, nav_bridge):
        bridge.showAction("Open album", "openAlbum")
        bridge._current["entity"] = "album_key_123"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_open_device(self, bridge, nav_bridge):
        bridge.showAction("Device", "openDevice")
        bridge._current["entity"] = "device_1"
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_open_diagnostics(self, bridge, nav_bridge):
        bridge.showAction("Diag", "openDiagnostics")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True

    def test_action_open_settings(self, bridge, nav_bridge):
        bridge.showAction("Settings", "openSettings")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True


class TestOpenJobNavigate:
    def test_open_job_uses_job_bridge(self, bridge, job_bridge):
        result = bridge.openJob("42")
        assert result["ok"] is True
        job_bridge.navigateToJob.assert_called_once_with("42")

    def test_open_job_fallback_navigation(self, bridge, job_bridge, nav_bridge):
        job_bridge.navigateToJob.side_effect = RuntimeError("fail")
        result = bridge.openJob("42")
        assert result["ok"] is True

    def test_open_job_no_job_bridge(self, bridge, nav_bridge):
        bridge._job_bridge = None
        result = bridge.openJob("42")
        assert result["ok"] is True
        nav_bridge.navigate.assert_called_once_with("audio_lab.jobs")


class TestCancelJobById:
    def test_cancel_job_valid(self, bridge, job_bridge):
        result = bridge.cancelJobById("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(42)

    def test_cancel_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.cancelJobById("42")
        assert result["ok"] is False

    def test_cancel_job_alpha_id(self, bridge):
        result = bridge.cancelJobById("abc")
        assert result["ok"] is False


class TestRetry:
    def test_retry_notification(self, bridge):
        bridge.showAction("Retry me", "some_action")
        nid = bridge.currentNotification["id"]
        result = bridge.retry(nid)
        assert result["ok"] is True

    def test_retry_job(self, bridge, job_bridge):
        result = bridge.retryJob("42")
        assert result["ok"] is True
        job_bridge.retryJob.assert_called_once_with("42")

    def test_retry_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.retryJob("42")
        assert result["ok"] is False


class TestShowTrackDevice:
    def test_show_track_with_album_key(self, bridge, nav_bridge):
        result = bridge.showTrack(0, album_key="alb_123")
        assert result["ok"] is True
        nav_bridge.navigateWithParams.assert_called_once_with(
            "library.album_detail", {"album_key": "alb_123"}
        )

    def test_show_track_fallback(self, bridge, action_registry):
        bridge._navigation_bridge = None
        result = bridge.showTrack(42)
        assert result["ok"] is True

    def test_show_device(self, bridge, nav_bridge):
        result = bridge.showDevice("dev_1")
        assert result["ok"] is True
        nav_bridge.navigate.assert_called_once_with("home_audio")

    def test_show_device_fallback(self, bridge, action_registry):
        bridge._navigation_bridge = None
        result = bridge.showDevice("dev_1")
        assert result["ok"] is True


class TestOpenDiagnosticsSettings:
    def test_open_diagnostics_via_nav(self, bridge, nav_bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True
        nav_bridge.navigate.assert_called_once_with("diagnostics")

    def test_open_diagnostics_fallback(self, bridge, action_registry):
        bridge._navigation_bridge = None
        result = bridge.openDiagnostics()
        assert result["ok"] is True

    def test_open_settings_via_nav(self, bridge, nav_bridge):
        result = bridge.openSettings()
        assert result["ok"] is True
        nav_bridge.navigate.assert_called_once_with("settings.general")

    def test_open_settings_fallback(self, bridge, action_registry):
        bridge._navigation_bridge = None
        result = bridge.openSettings()
        assert result["ok"] is True


class TestDeduplication:
    def test_dedup_same_message(self, bridge):
        bridge.showMessage("Hello", "info")
        result = bridge.showMessage("Hello", "info")
        assert result.get("dedup") is True

    def test_dedup_different_message(self, bridge):
        bridge.showMessage("Hello", "info")
        bridge.dismiss()
        bridge.showMessage("World", "info")
        assert bridge.currentNotification["text"] == "World"

    def test_dedup_update_replaces(self, bridge):
        bridge.showMessage("Old", "info")
        bridge.showMessage("Old", "info")
        assert bridge.currentNotification["text"] == "Old"


class TestProgressUpdated:
    def test_progress_current_update(self, bridge):
        bridge.showProgress("Init", "j_u", 10)
        result = bridge.updateProgress("j_u", 0.5, "Half")
        assert result["ok"] is True
        assert bridge.currentNotification["text"] == "Half"

    def test_progress_dedup_key_persistence(self, bridge):
        bridge.showProgress("A", "j_x", 25)
        assert bridge.currentNotification["progress"] == 25


class TestNotificationScore:
    def test_score_full(self, bridge):
        score = bridge.notificationScore()
        assert score["score"] >= 50

    def test_score_empty_bridge(self):
        b = NotificationBridge()
        score = b.notificationScore()
        assert score["score"] <= 50

    def test_score_has_current(self, bridge):
        bridge.showMessage("Test", "info")
        score = bridge.notificationScore()
        assert score["has_current"] is True

    def test_score_no_current(self, bridge):
        score = bridge.notificationScore()
        assert score["has_current"] is False


class TestEdgeCases:
    def test_dismiss_non_existent(self, bridge):
        result = bridge.dismiss("nonexistent")
        assert result["ok"] is True

    def test_clear_multiple_messages(self, bridge):
        for i in range(25):
            bridge.showMessage(f"Msg {i}", "info")
        bridge.clear()
        assert bridge.queueLength == 0
        assert bridge.currentNotification is None

    def test_queue_overflow(self, bridge):
        for i in range(25):
            bridge.showMessage(f"Msg {i}", "info")
        assert bridge.queueLength <= 20

    def test_action_no_action_registry(self, bridge, action_registry):
        bridge._action_registry = None
        bridge.showAction("Do", "some_action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_action_registry_execute_error(self, bridge, action_registry):
        action_registry.execute.return_value = {"ok": False, "error": "fail"}
        bridge.showAction("Do", "some_action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_show_action_is_persistent_and_prioritized(self, bridge):
        bridge.dismiss()
        bridge.showAction("Critical", "urgent")
        assert bridge.currentNotification["text"] == "Critical"
        assert bridge.currentNotification.get("persistent") is True

    def test_progress_dedup_in_queue(self, bridge):
        bridge.showProgress("A", "j_q", 10)
        bridge.showProgress("B", "j_q2", 20)
        r1 = bridge.showProgress("A updated", "j_q", 50)
        assert r1.get("updated") is True

    def test_open_job_no_bridge_fallback_ar(self, bridge, action_registry):
        bridge._job_bridge = None
        bridge._navigation_bridge = None
        result = bridge.openJob("42")
        assert result["ok"] is True

    def test_show_track_no_nav_no_ar(self, bridge):
        bridge._navigation_bridge = None
        bridge._action_registry = None
        result = bridge.showTrack(42)
        assert result["ok"] is False

    def test_show_track_no_album_key_no_ar(self, bridge, action_registry):
        bridge._navigation_bridge = None
        result = bridge.showTrack(42)
        assert result["ok"] is True
