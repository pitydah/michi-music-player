"""Test keyboard navigation for devices pages.

Tests focus on the DevicesBridge and DeviceSyncService layers,
verifying that slot-based navigation contracts work correctly.
"""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = [
        {"alias": "Device1", "device": "android", "ip": "192.168.1.10", "port": 53318},
        {"alias": "Device2", "device": "android", "ip": "192.168.1.11", "port": 53318},
    ]
    mgr.get_paired_devices.return_value = [
        {"alias": "My Phone", "device": "android"},
    ]
    mgr.is_active = True
    return mgr


@pytest.fixture
def nav_bridge():
    bridge = NavigationBridge()
    bridge.set_capabilities({"devices"})
    return bridge


@pytest.fixture
def bridge(mock_sync_mgr):
    return DevicesBridge(sync_manager=mock_sync_mgr)


class TestDeviceKeyboardNavigation:
    def test_device_list_navigation(self, bridge):
        """Verify bridge provides device list data for keyboard navigation."""
        bridge.refresh()
        assert len(bridge.pairedDevices) >= 1
        assert len(bridge.peers) >= 2

    def test_navigate_to_device_detail(self, nav_bridge):
        """Verify NavigationBridge can navigate to device detail route."""
        nav_bridge.navigateWithParams("devices.detail", {"device_id": "test_device"})
        assert nav_bridge.currentRoute == "devices.detail"
        params = nav_bridge.currentParams
        assert params.get("device_id") == "test_device"

    def test_navigate_back_from_detail(self, nav_bridge):
        """Verify NavigationBridge can go back from device detail."""
        nav_bridge.navigateWithParams("devices.detail", {"device_id": "test_device"})
        assert nav_bridge.canGoBack is True
        nav_bridge.back()
        assert nav_bridge.currentRoute != "devices.detail"

    def test_navigate_to_pairing_page(self, nav_bridge):
        """Verify NavigationBridge can navigate to pairing page."""
        nav_bridge.navigateWithParams("devices.pairing", {})
        assert nav_bridge.currentRoute == "devices.pairing"

    def test_navigate_forward_after_back(self, nav_bridge):
        """Verify forward navigation after going back works."""
        nav_bridge.navigate("home")
        nav_bridge.navigateWithParams("devices.detail", {"device_id": "d1"})
        nav_bridge.back()
        assert nav_bridge.canGoForward is True
        nav_bridge.forward()
        assert nav_bridge.currentRoute == "devices.detail"

    def test_invalid_route_shows_placeholder(self, nav_bridge):
        """Verify invalid route resolves to placeholder."""
        nav_bridge.navigate("invalid_device_route")
        assert nav_bridge.currentRoute == "placeholder"

    def test_device_detail_back_stack(self, nav_bridge):
        """Verify device detail adds to back stack."""
        nav_bridge.navigate("home")
        nav_bridge.navigateWithParams("devices.detail", {"device_id": "d1"})
        nav_bridge.navigateWithParams("devices.detail", {"device_id": "d2"})
        nav_bridge.back()
        params = nav_bridge.currentParams
        assert params.get("device_id") == "d1"

    def test_server_toggle_via_keyboard(self, bridge):
        """Verify server toggle works as keyboard action."""
        result = bridge.startServer()
        assert result["ok"] is True
        assert bridge.serverActive is True

        result = bridge.stopServer()
        assert result["ok"] is True
        assert bridge.serverActive is False

    def test_server_action_no_manager(self):
        """Verify keyboard action with null manager returns error."""
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startServer()
        assert result["ok"] is False
        assert result["error"] == "NO_SYNC_MANAGER"

    def test_device_unpair_action(self, bridge, mock_sync_mgr):
        """Verify unpair action works."""
        bridge.refresh()
        result = bridge.unpairDevice("test_key")
        assert result["ok"] is False

    def test_device_authorize_action(self, bridge):
        """Verify authorize action works."""
        bridge.refresh()
        result = bridge.authorizeDevice("test_key")
        assert result["ok"] is False

    def test_refresh_server_state(self, bridge):
        """Verify refresh updates server state."""
        bridge.refresh()
        assert bridge.serverActive is True
