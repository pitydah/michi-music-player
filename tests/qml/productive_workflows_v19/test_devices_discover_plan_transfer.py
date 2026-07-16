"""Workflow: Devices → Discover → Plan → Transfer → Cancel."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("devices"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestDevices:
    def test_device_discover_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        for aid in ("device.discover", "device.sync.start", "device.sync.cancel"):
            a = ar.get(aid)
            assert a is not None, f"{aid} action exists"

    def test_device_sync_service_methods(self, bootstrap):
        svc = bootstrap.container.get("device_sync_service")
        assert svc is not None
        assert hasattr(svc, 'discover')
        assert hasattr(svc, 'start_sync')
        assert hasattr(svc, 'cancel_sync')
        assert hasattr(svc, 'free_space')
        assert hasattr(svc, 'formats')
        assert hasattr(svc, 'profiles')
        assert hasattr(svc, 'transcode_policy')
        assert hasattr(svc, 'naming_policy')
        assert hasattr(svc, 'collision_policy')
        assert hasattr(svc, 'sync_plan')
        assert hasattr(svc, 'size_estimate')
        assert hasattr(svc, 'eject')

    def test_devices_bridge_exists(self, bootstrap, bridges):
        db = bridges.get("devices")
        assert db is not None
