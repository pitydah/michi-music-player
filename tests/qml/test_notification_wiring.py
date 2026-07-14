"""Test NotificationBridge wiring — created after ActionRegistry and JobBridge, exposed via read-only properties."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.job_bridge import JobBridge
from core.worker_manager import WorkerManager


@pytest.fixture
def action_registry():
    return ActionRegistry()


@pytest.fixture
def worker_manager():
    return MagicMock(spec=WorkerManager)


@pytest.fixture
def job_bridge(worker_manager):
    return JobBridge(worker_manager=worker_manager)


class TestWiring:
    def test_created_after_action_registry(self, action_registry):
        bridge = NotificationBridge(action_registry=action_registry)
        assert bridge.action_registry is action_registry

    def test_created_after_job_bridge(self, job_bridge):
        bridge = NotificationBridge(job_bridge=job_bridge)
        assert bridge.job_bridge is job_bridge

    def test_accepts_both_dependencies(self, action_registry, job_bridge):
        bridge = NotificationBridge(
            action_registry=action_registry,
            job_bridge=job_bridge,
        )
        assert bridge.action_registry is action_registry
        assert bridge.job_bridge is job_bridge

    def test_read_only_action_registry(self, action_registry):
        bridge = NotificationBridge(action_registry=action_registry)
        assert bridge.action_registry is action_registry

    def test_read_only_job_bridge(self, job_bridge):
        bridge = NotificationBridge(job_bridge=job_bridge)
        assert bridge.job_bridge is job_bridge

    def test_read_only_current(self):
        bridge = NotificationBridge()
        assert bridge.current is None
        bridge.showMessage("Test")
        assert bridge.current is not None

    def test_read_only_queue(self):
        bridge = NotificationBridge()
        assert bridge.queue == []
        bridge.showMessage("A")
        bridge.showMessage("B")
        assert len(bridge.queue) == 1

    def test_wiring_no_circular_dependency(self):
        ar = ActionRegistry()
        jb = MagicMock()
        nb = NotificationBridge(action_registry=ar, job_bridge=jb)
        assert nb._action_registry is ar
        assert nb._job_bridge is jb

    def test_notification_uses_action_registry_execute(self):
        ar = MagicMock()
        ar.execute.return_value = {"ok": True}
        nb = NotificationBridge(action_registry=ar)
        nb.showAction("Test", "navigate_home")
        result = nb.executeCurrentAction()
        assert result["ok"] is True
        ar.execute.assert_called_with("navigate_home")

    def test_notification_uses_job_bridge_cancel(self):
        jb = MagicMock()
        jb.cancelJob.return_value = {"ok": True}
        nb = NotificationBridge(job_bridge=jb)
        nb.cancelJob("1")
        jb.cancelJob.assert_called_with(1)

    def test_notification_properties_accessible_from_qml(self):
        nb = NotificationBridge()
        assert hasattr(nb, 'currentNotification')
        assert hasattr(nb, 'queueLength')
        assert hasattr(nb, 'notificationChanged')
        assert hasattr(nb, 'notificationCountChanged')
        assert hasattr(nb, 'actionExecuted')

    def test_queue_property_reflects_state(self):
        nb = NotificationBridge()
        assert nb.queueLength == 0
        nb.showMessage("Msg 1")
        nb.showMessage("Msg 2")
        assert nb.queueLength == 1
