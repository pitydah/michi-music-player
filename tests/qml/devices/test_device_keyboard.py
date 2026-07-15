<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test keyboard navigation for devices pages.

Tests focus on the DevicesBridge and DeviceSyncService layers,
verifying that slot-based navigation contracts work correctly.
"""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test keyboard navigation for Devices pages."""
from __future__ import annotations

=======
"""Test keyboard navigation for devices pages.

Tests focus on the DevicesBridge and DeviceSyncService layers,
verifying that slot-based navigation contracts work correctly.
"""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge
<<<<<<< Updated upstream
<<<<<<< Updated upstream
from ui_qml_bridge.navigation_bridge import NavigationBridge

=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
from ui_qml_bridge.navigation_bridge import NavigationBridge

>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

pytestmark = pytest.mark.isolation


<<<<<<< Updated upstream
<<<<<<< Updated upstream
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


=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
    def test_generate_qr_slot(self):
        b = DevicesBridge()
        qr = b.generateQRCode()
        assert isinstance(qr, str)
        assert qr.startswith("michi://pair/")

    def test_trust_device_slot(self):
        svc = MagicMock()
        svc.trust.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.trustDevice("test-key")
        assert result["ok"] is True

    def test_cancel_transfer_slot(self):
        svc = MagicMock()
        svc.cancel_job.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.cancelTransfer("job-1")
        assert result["ok"] is True

    def test_retry_transfer_slot(self):
        svc = MagicMock()
        svc.retry_job.return_value = {"ok": True}
        b = DevicesBridge(device_sync_service=svc)
        result = b.retryTransfer("job-1")
        assert result["ok"] is True

    def test_validate_audio_slot(self):
        b = DevicesBridge()
        result = b.validateAudioFile("/music/track.flac")
        assert result["ok"] is False  # File doesn't exist

    def test_eject_device_slot(self):
        svc = MagicMock()
        svc.eject.return_value = True
        b = DevicesBridge(device_sync_service=svc)
        result = b.ejectDevice("/media/test")
        assert result["ok"] is True

    def test_browse_files_slot(self):
        svc = MagicMock()
        svc.list_music.return_value = [{"name": "track.flac"}]
        b = DevicesBridge(device_sync_service=svc)
        result = b.browseFiles("/media/test", "Music")
        assert result["ok"] is True
        assert len(result["files"]) == 1

    def test_get_device_icon_slot(self):
        b = DevicesBridge()
        icon = b.getDeviceIcon("android")
        assert isinstance(icon, str)
        assert icon == "smartphone"

    def test_clear_history_slot(self):
        svc = MagicMock()
        b = DevicesBridge(device_sync_service=svc)
        result = b.clearTransferHistory()
        assert result["ok"] is True
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_refresh_server_state(self, bridge):
        """Verify refresh updates server state."""
        bridge.refresh()
        assert bridge.serverActive is True
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
