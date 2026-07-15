"""Test DevicesPage state machine, server controls, device list."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge, STATE_UNAVAILABLE, STATE_LOADING, STATE_READY, STATE_EMPTY, STATE_ERROR

pytestmark = pytest.mark.isolation


class TestDevicesPageStates:
    def test_initial_state_unavailable(self):
        b = DevicesBridge()
        assert b.pageState == STATE_UNAVAILABLE

    def test_unavailable_when_no_manager(self):
        b = DevicesBridge()
        assert b.bridgeAvailable is True

    def test_available_when_manager_present(self):
        mgr = MagicMock()
        b = DevicesBridge(sync_manager=mgr)
        assert b.bridgeAvailable is True

    def test_state_transitions_to_ready(self):
        mgr = MagicMock()
        mgr.get_all_peers.return_value = [{"alias": "P1", "device": "android"}]
        mgr.get_paired_devices.return_value = [{"alias": "P2", "device": "android"}]
        mgr.is_active = True
        b = DevicesBridge(sync_manager=mgr)
        b.startServer()
        b.refresh()
        assert b.pageState == STATE_READY

    def test_state_empty_after_start_no_devices(self):
        mgr = MagicMock()
        mgr.get_all_peers.return_value = []
        mgr.get_paired_devices.return_value = []
        mgr.is_active = True
        b = DevicesBridge(sync_manager=mgr)
        b._server_active = True
        b._set_state()
        assert b.pageState == STATE_EMPTY

    def test_state_error(self):
        b = DevicesBridge()
        b.errorMessage = "Connection failed"
        b._set_state()
        assert b.pageState == STATE_ERROR

    def test_state_loading_when_manager_no_server(self):
        mgr = MagicMock()
        b = DevicesBridge(sync_manager=mgr)
        assert b.pageState == STATE_LOADING

    def test_state_unavailable_no_bridge(self):
        b = DevicesBridge()
        b._bridge_available = False
        b._set_state()
        assert b.pageState == STATE_UNAVAILABLE


class TestDevicesPageServerControls:
    def test_server_start_stop(self):
        mgr = MagicMock()
        mgr.start.return_value = True
        mgr.stop.return_value = True
        b = DevicesBridge(sync_manager=mgr)
        result = b.startServer()
        assert result["ok"] is True
        assert b.serverActive is True
        result = b.stopServer()
        assert result["ok"] is True
        assert b.serverActive is False

    def test_server_start_no_manager_fails(self):
        b = DevicesBridge()
        result = b.startServer()
        assert result["ok"] is False

    def test_server_port_default(self):
        b = DevicesBridge()
        assert b.serverPort == 53318

    def test_server_port_custom(self):
        mgr = MagicMock()
        b = DevicesBridge(sync_manager=mgr)
        assert b.serverPort == 53318

    def test_server_active_emits_signal(self):
        mgr = MagicMock()
        mgr.start.return_value = True
        b = DevicesBridge(sync_manager=mgr)
        signals = []
        b.stateChanged.connect(lambda: signals.append(1))
        b.startServer()
        assert len(signals) >= 1


class TestDevicesPageDeviceList:
    def test_paired_devices_initial_empty(self):
        b = DevicesBridge()
        assert b.pairedDevices == []

    def test_peers_initial_empty(self):
        b = DevicesBridge()
        assert b.peers == []

    def test_refresh_populates_peers(self):
        mgr = MagicMock()
        mgr.get_all_peers.return_value = [
            {"alias": "Phone", "device": "android", "ip": "192.168.1.50", "port": 53318},
        ]
        b = DevicesBridge(sync_manager=mgr)
        b.refresh()
        assert len(b.peers) == 1
        assert b.peers[0]["alias"] == "Phone"

    def test_refresh_populates_paired(self):
        mgr = MagicMock()
        mgr.get_paired_devices.return_value = [{"alias": "My Phone", "device": "android"}]
        b = DevicesBridge(sync_manager=mgr)
        b.refresh()
        assert len(b.pairedDevices) == 1

    def test_refresh_no_manager_returns_ok(self):
        b = DevicesBridge()
        result = b.refresh()
        assert result["ok"] is True

    def test_peers_multiple_devices(self):
        mgr = MagicMock()
        mgr.get_all_peers.return_value = [
            {"alias": "P1", "device": "android"},
            {"alias": "P2", "device": "tablet"},
            {"alias": "P3", "device": "desktop"},
        ]
        b = DevicesBridge(sync_manager=mgr)
        b.refresh()
        assert len(b.peers) == 3

    def test_connect_to_peer(self):
        mgr = MagicMock()
        mgr.connect.return_value = {"ok": True}
        b = DevicesBridge(sync_manager=mgr)
        result = b.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is True

    def test_connect_to_peer_no_manager(self):
        b = DevicesBridge()
        result = b.connectToPeer("192.168.1.50", 53318)
        assert result["ok"] is False

    def test_discover_devices_no_service(self):
        b = DevicesBridge()
        result = b.discoverDevices()
        assert result["ok"] is False

    def test_get_device_icon_known(self):
        b = DevicesBridge()
        assert b.getDeviceIcon("android") == "smartphone"
        assert b.getDeviceIcon("desktop") == "desktop"
        assert b.getDeviceIcon("tablet") == "tablet"
        assert b.getDeviceIcon("hiby") == "music_note"
        assert b.getDeviceIcon("sandisk") == "sd_card"

    def test_get_device_icon_unknown(self):
        b = DevicesBridge()
        assert b.getDeviceIcon("unknown") == "devices"

    def test_generate_qr_code(self):
        b = DevicesBridge()
        qr = b.generateQRCode()
        assert qr.startswith("michi://pair/")
        assert b.qrCodeData == qr
