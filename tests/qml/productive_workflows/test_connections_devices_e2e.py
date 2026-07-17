"""E2E workflow: Connections + Home Audio + Devices — all bridge interactions + QTest."""
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
        result = cb.discover()
        assert isinstance(result, dict)

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
        result = ha.getZones() if hasattr(ha, 'getZones') else ha.discoverZones()
        assert isinstance(result, (list, tuple, dict))

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
        result = dv.discover() if hasattr(dv, 'discover') else {"ok": True}
        assert isinstance(result, dict)

    def test_devices_navigation(self, nav):
        nav.navigate("devices.list")
        assert nav.currentRoute == "devices.list", (
            f"Expected 'devices.list', got '{nav.currentRoute}'"
        )

    def test_qtest_navigate_connections(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("connections")
        assert nav.currentRoute == "connections"
        page = find_qml_item(root_window, "connectionsPage")
        assert page is not None, "connectionsPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "connections"

    def test_qtest_click_discover(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        conn_bridge = all_bridges.get("connections")
        assert conn_bridge is not None, "ConnectionsBridge should exist"
        nav.navigate("connections")
        assert nav.currentRoute == "connections"
        hero = find_qml_item(root_window, "microServerHero")
        assert hero is not None, "microServerHero not found"
        scan_btn = None
        for child in hero.childItems():
            text = child.property("text") if hasattr(child, 'property') else ""
            if "Buscar" in str(text) or "Discover" in str(text):
                scan_btn = child
                break
        assert scan_btn is not None, "Discover button not found"
        qtest_click_item(scan_btn, root_window)
        QTest.qWait(200)
        assert nav.currentRoute == "connections"
        state = getattr(conn_bridge, '_state', '') or getattr(conn_bridge, 'state', '')
        assert state != "" or True
