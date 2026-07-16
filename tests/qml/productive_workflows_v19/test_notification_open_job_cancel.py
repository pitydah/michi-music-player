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
            assert hasattr(svc, 'retry') or hasattr(svc, 'undo')
            assert hasattr(svc, 'open_job') or hasattr(svc, 'open_track')
            assert hasattr(svc, 'open_settings') or hasattr(svc, 'open_diagnostics')

    def test_notification_bridge_exists(self, bootstrap):
        nb = bootstrap._bridges.get("notification")
        assert nb is not None
