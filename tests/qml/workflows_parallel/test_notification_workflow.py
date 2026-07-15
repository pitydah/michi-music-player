from __future__ import annotations
"""Full workflow: show progress -> open center -> click cancel -> verify job state.
Tests the complete notification lifecycle across bridges:
1. Show a progress notification via NotificationBridge
2. Verify it appears as current notification
3. Update progress through multiple steps
4. Cancel the job via JobBridge
5. Dismiss the notification
6. Verify center is empty
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.job_bridge import JobBridge
from ui_qml_bridge.action_registry import ActionRegistry
from core.worker_manager import WorkerManager


@pytest.fixture
def worker_manager():
    return MagicMock(spec=WorkerManager)


@pytest.fixture
def job_bridge(worker_manager):
    return JobBridge(worker_manager=worker_manager)


@pytest.fixture
def action_registry():
    return ActionRegistry()


@pytest.fixture
def bridge(action_registry, job_bridge):
    return NotificationBridge(
        action_registry=action_registry,
        job_bridge=job_bridge,
    )


class TestNotificationWorkflow:
    def test_show_progress_through_bridge(self, bridge):
        result = bridge.showProgress("Escaneando biblioteca...", "scan_1", 0)
        assert result["ok"] is True
        current = bridge.currentNotification
        assert current is not None
        assert current["kind"] == "info"
        assert current["progress"] == 0
        assert current["job_id"] == "scan_1"
        assert current["persistent"] is True

    def test_update_progress_reflects_in_current(self, bridge):
        bridge.showProgress("Indexando...", "idx_1", 0)
        bridge.updateProgress("idx_1", 0.5, "50% indexado")
        current = bridge.currentNotification
        assert current["progress"] >= 50
        assert current["text"] == "50% indexado"

    def test_update_progress_to_completion(self, bridge):
        bridge.showProgress("Comprimiendo...", "cmp_1", 0)
        for pct in [25, 50, 75]:
            bridge.updateProgress("cmp_1", pct / 100.0, f"{pct}% completado")
        bridge.updateProgress("cmp_1", 1.0, "100% completado")
        assert bridge.currentNotification["progress"] >= 1

    def test_progress_is_persistent(self, bridge):
        bridge.showProgress("Descarga", "dl_1", 30)
        n = bridge.currentNotification
        assert n is not None
        assert n["persistent"] is True
        assert n["job_id"] == "dl_1"

    def test_cancel_job_transitions_state(self, bridge, job_bridge):
        bridge.showProgress("Trabajo largo", "long_1", 50)
        job_bridge._add_job("library_scan", "Trabajo largo")
        result = bridge.cancelJobById("1")
        assert result["ok"] is True

    def test_dismiss_progress_notification(self, bridge):
        bridge.showProgress("Tarea", "t_1", 50)
        assert bridge.currentNotification is not None
        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_full_lifecycle_show_update_cancel_dismiss(self, bridge, job_bridge):
        bridge.showProgress("Sincronizando...", "sync_1", 0)
        assert bridge.currentNotification is not None

        for i in range(1, 6):
            bridge.updateProgress("sync_1", i * 20 / 100.0, f"{i * 20}%")

        bridge.updateProgress("sync_1", 1.0, "100%")
        assert bridge.currentNotification["progress"] >= 1

        job_bridge._add_job("library_scan", "Sincronizando")
        cancel_result = bridge.cancelJobById("1")
        assert cancel_result["ok"] is True

        bridge.dismiss()
        assert bridge.currentNotification is None

    def test_center_empty_after_full_clear(self, bridge):
        bridge.showProgress("Tarea A", "a", 10)
        bridge.showMessage("Notificacion B")
        bridge.showAction("Notificacion C", "navigate_home")
        assert bridge.queueLength > 0 or bridge.currentNotification is not None

        bridge.clear()
        assert bridge.currentNotification is None
        assert bridge.queueLength == 0
        assert len(bridge._queue) == 0

    def test_center_shows_only_active_notifications(self, bridge):
        bridge.showProgress("Activo", "active_1", 50)
        assert bridge.currentNotification is not None

        bridge.showMessage("En cola")
        assert bridge.queueLength == 1

        bridge.dismiss()
        assert bridge.currentNotification is not None
        assert bridge.currentNotification["text"] == "En cola"

    def test_show_action_has_high_priority(self, bridge):
        bridge.showAction("Urgente", "navigate_home")
        assert bridge.currentNotification["action"] == "navigate_home"
        assert bridge.currentNotification["persistent"] is True

    def test_cancel_job_uses_job_bridge(self, bridge, job_bridge):
        job_bridge._add_job("library_scan", "Progreso")
        bridge.showProgress("Progreso", "1", 50)
        result = bridge.cancelJobById("1")
        assert result["ok"] is True
