"""E2E workflow: Connections + Home Audio + Devices — all bridge interactions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("connections"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("connections"),
]


class TestConnectionsDevicesE2E:
    def test_connections_bridge_exists(self, all_bridges):
        cb = all_bridges.get("connections")
        assert cb is not None, "ConnectionsBridge should exist"

    def test_connections_list(self, all_bridges):
        cb = all_bridges.get("connections")
        assert cb is not None
        result = cb.listConnections()
        assert isinstance(result, (list, tuple))

    def test_connections_navigation(self, nav):
        nav.navigate("connections")
        assert nav.currentRoute == "connections", (
            f"Expected 'connections', got '{nav.currentRoute}'"
        )

    def test_home_audio_bridge_exists(self, all_bridges):
        ha = all_bridges.get("home_audio")
        assert ha is not None, "HomeAudioBridge should exist"

    def test_home_audio_get_zones(self, all_bridges):
        ha = all_bridges.get("home_audio")
        assert ha is not None
        result = ha.getZones()
        assert isinstance(result, (list, tuple))

    def test_home_audio_navigation(self, nav):
        nav.navigate("home_audio")
        assert nav.currentRoute == "home_audio", (
            f"Expected 'home_audio', got '{nav.currentRoute}'"
        )

    def test_devices_bridge_exists(self, all_bridges):
        dv = all_bridges.get("devices")
        assert dv is not None, "DevicesBridge should exist"

    def test_devices_list(self, all_bridges):
        dv = all_bridges.get("devices")
        assert dv is not None
        result = dv.listDevices()
        assert isinstance(result, (list, tuple))

    def test_devices_navigation(self, nav):
        nav.navigate("devices.list")
        assert nav.currentRoute == "devices.list", (
            f"Expected 'devices.list', got '{nav.currentRoute}'"
        )
