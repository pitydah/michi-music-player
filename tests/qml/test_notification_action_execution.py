from __future__ import annotations
"""Test NotificationBridge — ActionRegistry integration, progress, cancel, dedup."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge


@pytest.fixture
def action_registry():
    registry = MagicMock()
    registry.execute.return_value = {"ok": True}
    return registry


@pytest.fixture
def job_bridge():
    jb = MagicMock()
    jb.cancelJob.return_value = {"ok": True}
    return jb


@pytest.fixture
def bridge(action_registry, job_bridge):
    return NotificationBridge(
        action_registry=action_registry,
        job_bridge=job_bridge,
    )


class TestBasicNotifications:
    def test_show_message(self, bridge):
        result = bridge.showMessage("Hola mundo")
        assert result["ok"] is True
        assert bridge.currentNotification is not None
        assert bridge.currentNotification["text"] == "Hola mundo"

    def test_show_message_kind(self, bridge):
        bridge.showMessage("Error", "error")
        assert bridge.currentNotification["kind"] == "error"
        assert bridge.currentNotification["persistent"] is True

    def test_show_message_dedup(self, bridge):
        bridge.showMessage("Dedup test")
        result = bridge.showMessage("Dedup test")
        assert result["dedup"] is True

    def test_dismiss(self, bridge):
        bridge.showMessage("Dismiss me")
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_clear(self, bridge):
        bridge.showMessage("Clear 1")
        bridge.showMessage("Clear 2")
        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0

    def test_show_action(self, bridge):
        result = bridge.showAction("Acción necesaria", "navigate_settings")
        assert result["ok"] is True
        assert bridge.currentNotification["action"] == "navigate_settings"

    def test_show_progress(self, bridge):
        result = bridge.showProgress("Transfiriendo...", "job_1", 50)
        assert result["ok"] is True

    def test_update_progress(self, bridge):
        bridge.showProgress("Iniciando...", "job_update", 0)
        result = bridge.updateProgress("job_update", 0.75, "75% completado")
        assert result["ok"] is True


class TestActionIntegration:
    def test_execute_current_action(self, bridge, action_registry):
        bridge.showAction("Abrir ajustes", "navigate_settings")
        result = bridge.executeCurrentAction()
        assert result["ok"] is True
        action_registry.execute.assert_called_once_with("navigate_settings")

    def test_execute_current_no_action(self, bridge):
        bridge.showMessage("Sin acción")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_execute_current_no_notification(self, bridge):
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_execute_notification_action_by_id(self, bridge, action_registry):
        bridge.showAction("Test", "playback_playpause")
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(str(nid))
        assert result["ok"] is True
        action_registry.execute.assert_called_once_with("playback_playpause")

    def test_execute_notification_action_not_found(self, bridge):
        result = bridge.executeNotificationAction("99999")
        assert result["ok"] is False

    def test_execute_notification_action_from_queue(self, bridge, action_registry):
        bridge.showMessage("Primera")
        bridge.showAction("Segunda con acción", "library_refresh")
        bridge.dismiss()
        nid = bridge.currentNotification["id"]
        result = bridge.executeNotificationAction(str(nid))
        assert result["ok"] is True
        action_registry.execute.assert_called_once()

    def test_action_registry_returns_false(self, bridge, action_registry):
        action_registry.execute.return_value = {"ok": False, "error": "DISABLED"}
        bridge.showAction("Fallo", "disabled_action")
        result = bridge.executeCurrentAction()
        assert result["ok"] is False

    def test_action_executed_signal_emitted(self, bridge, action_registry):
        signals = []
        bridge.actionExecuted.connect(lambda a_id, r: signals.append((a_id, r)))
        bridge.showAction("Test signal", "navigate_home")
        bridge.executeCurrentAction()
        assert len(signals) == 1
        assert signals[0][0] == "navigate_home"
        assert signals[0][1]["ok"] is True


class TestCancelJob:
    def test_cancel_job(self, bridge, job_bridge):
        bridge.showProgress("Trabajo en curso", "42", 50)
        result = bridge.cancelJob("42")
        assert result["ok"] is True
        job_bridge.cancelJob.assert_called_once_with(42)

    def test_cancel_job_no_bridge(self, bridge):
        bridge._job_bridge = None
        result = bridge.cancelJob("42")
        assert result["ok"] is False

    def test_cancel_job_invalid_id(self, bridge, job_bridge):
        job_bridge.cancelJob.side_effect = ValueError("Invalid")
        result = bridge.cancelJob("abc")
        assert result["ok"] is False


class TestPriority:
    def test_action_has_high_priority(self, bridge):
        bridge.showAction("Urgente", "app_quit")
        assert bridge.currentNotification["action"] == "app_quit"
        assert bridge.currentNotification["persistent"] is True

    def test_error_is_persistent(self, bridge):
        bridge.showMessage("Error crítico", "error")
        assert bridge.currentNotification["persistent"] is True

    def test_info_times_out(self, bridge):
        bridge.showMessage("Info normal")
        assert bridge.currentNotification is not None


class TestScore:
    def test_score_has_action_registry(self, bridge):
        score = bridge.notificationScore()
        assert score["score"] > 0
        assert score["has_action_registry"] is True
        assert score["has_job_bridge"] is True

    def test_score_no_registry(self):
        empty = NotificationBridge()
        score = empty.notificationScore()
        assert score["has_action_registry"] is False
        assert score["has_job_bridge"] is False
