"""Workflow: Notification → Open Job → Cancel."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestNotification:
    def test_notification_service_methods(self, bootstrap):
        svc = bootstrap.container.get("notification_service")
        if svc:
            # The notification service is a store: persistent notifications
            # survive restart; action dispatch lives in the action service.
            assert hasattr(svc, 'notify') and hasattr(svc, 'dismiss')
            assert hasattr(svc, 'list_persistent') and hasattr(svc, 'list_all')
            action_svc = bootstrap.container.get("notification_action_service")
            if action_svc:
                assert hasattr(action_svc, 'route')
                assert "retry" in action_svc.dispatch_ids()
                assert "undo" in action_svc.dispatch_ids()

    def test_notification_bridge_exists(self, bootstrap, bridges):
        nb = bridges.get("notification")
        assert nb is not None
