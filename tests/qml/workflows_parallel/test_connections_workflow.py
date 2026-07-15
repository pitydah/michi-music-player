"""Full workflow: discover -> connect -> disconnect -> reconnect -> forget."""
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    s1, s2 = MagicMock(), MagicMock()
    s1.name = "Server1"
    s1.host = "10.0.0.1"
    s2.name = "Server2"
    s2.host = "10.0.0.2"
    ctrl.discover_servers.return_value = [s1, s2]
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MyServer",
        "contract_ok": True,
        "can_continue_playback": True,
        "can_import": True,
        "can_send_genre_playlist": True,
        "can_send_genre_mix": False,
    }
    ctrl.reconnect.return_value = True
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MyServer",
    }
    ctrl.is_connected = True
    ctrl.connect = MagicMock(return_value={"ok": True})
    ctrl.test_connection = MagicMock(return_value=True)
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(michi_link_ctrl=mock_ctrl)


class TestFullWorkflow:
    def test_discover_scan(self, bridge, mock_ctrl):
        result = bridge.scanForServers()
        assert result["ok"] is True
        assert mock_ctrl.discover_servers.called
        assert len(bridge.discoveredServers) == 2

    def test_connect_manual(self, bridge):
        result = bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert result["ok"] is True
        assert bridge.microServerAlias == "MyServer"

    def test_disconnect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
        assert bridge.latencyMs == 0

    def test_reconnect(self, bridge, mock_ctrl):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called

    def test_forget(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.forgetServer()
        assert bridge.microServerState == "not_configured"
        assert bridge.microServerAlias == ""

    def test_scan_then_connect_then_diagnose(self, bridge):
        bridge.scanForServers()
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        result = bridge.diagnose()
        assert result["ok"] is True

    def test_connect_then_disconnect_then_scan(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Srv")
        bridge.disconnect()
        result = bridge.scanForServers()
        assert result["ok"] is True

    def test_scan_then_add_manual(self, bridge):
        bridge.scanForServers()
        result = bridge.addManualServer("10.0.0.1", 53318, "New")
        assert result["ok"] is True
        assert bridge.microServerState == "detected"

    def test_pair_then_confirm_then_disconnect(self, bridge):
        bridge.requestPair()
        assert bridge.microServerState == "pairing_required"
        bridge.confirmPair()
        assert bridge.microServerState == "connected"
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"

    def test_connect_then_diagnose_then_reconnect(self, bridge, mock_ctrl):
        bridge.connectManual("10.0.0.1", 53318, "Srv")
        bridge.diagnose()
        assert bridge.serverVersion == "MyServer"
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called

    def test_scan_then_cancel_then_scan_again(self, bridge):
        bridge.scanForServers()
        bridge.scanForServers()
        assert len(bridge.discoveredServers) == 2

    def test_connect_then_refresh_then_disconnect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.refresh()
        assert bridge.microServerState != "error"
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"

    def test_full_lifecycle(self, bridge, mock_ctrl):
        bridge.scanForServers()
        assert len(bridge.discoveredServers) == 2
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert bridge.microServerAlias == "MyServer"
        bridge.diagnose()
        assert bridge.serverVersion == "MyServer"
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
        bridge.reconnect()
        assert mock_ctrl.reconnect.called
        bridge.forgetServer()
        assert bridge.microServerAlias == ""

    def test_add_manual_then_connect_manual(self, bridge):
        bridge.addManualServer("10.0.0.1", 53318, "Added")
        result = bridge.connectManual("10.0.0.1", 53318, "Connected")
        assert result["ok"] is True
        assert bridge.microServerAlias == "Connected"

    def test_no_controller_full_workflow(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.scanForServers()
        assert b.discoveredServers == []
        b.connectManual("10.0.0.1", 53318, "X")
        assert b.microServerAlias == "X"
        b.disconnect()
        assert b.microServerState == "not_configured"
        b.reconnect()
        assert b.microServerState == "scanning"
        b.forgetServer()
        assert b.microServerAlias == ""
