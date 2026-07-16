"""Workflow: Device functions — discover, sync start, sync cancel."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("devices"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestDeviceFunctions:
    def test_device_discover_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("device.discover")
        assert a is not None and a.handler is not None

    def test_device_sync_start_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("device.sync.start")
        assert a is not None and a.handler is not None

    def test_device_sync_cancel_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("device.sync.cancel")
        assert a is not None and a.handler is not None

    def test_device_sync_service_exists(self, bootstrap):
        svc = bootstrap.container.get("device_sync_service")
        assert svc is not None
        assert hasattr(svc, 'discover')
        assert hasattr(svc, 'start_sync')
        assert hasattr(svc, 'cancel_sync')

    def test_devices_bridge_exists(self, bootstrap):
        bridge = bootstrap._bridges.get("devices")
        assert bridge is not None
