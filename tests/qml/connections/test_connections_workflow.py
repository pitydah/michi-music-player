"""Test Connections workflows through ConnectionsBridge."""
from unittest.mock import MagicMock


from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation



@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    s1, s2 = MagicMock(), MagicMock()
    s1.name = "MichiServer1"
    s1.host = "192.168.1.100"
    s2.name = "MichiServer2"
    s2.host = "192.168.1.101"
    ctrl.discover_servers.return_value = [s1, s2]
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "Michi Micro Server",
        "contract_ok": True,
        "can_continue_playback": True,
        "can_import": False,
        "can_send_genre_playlist": True,
        "can_send_genre_mix": False,
    }
    ctrl.reconnect.return_value = True
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "Michi Server",
    }
    ctrl.is_connected = True
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(michi_link_ctrl=mock_ctrl)


class TestInitialState:
    def test_start_not_configured(self, bridge):
        assert bridge.microServerState == "not_configured"
        assert bridge.lastError == ""
        assert bridge.latencyMs == 0

    def test_discovered_empty_initially(self, bridge):
        assert bridge.discoveredServers == []

    def test_capabilities_list_shape(self, bridge):
        caps = bridge.capabilities
        assert isinstance(caps, list)
        assert len(caps) == 4


class TestDiscovery:
    def test_scan_returns_servers(self, bridge, mock_ctrl):
        result = bridge.scanForServers()
        assert result["ok"] is True
        assert mock_ctrl.discover_servers.called

    def test_scan_populates_discovered(self, bridge):
        bridge.scanForServers()
        assert len(bridge.discoveredServers) == 2
        assert bridge.discoveredServers[0]["name"] == "MichiServer1"

    def test_scan_overwrites_discovered(self, bridge):
        bridge.scanForServers()
        assert bridge.microServerState != "not_configured"

    def test_scan_cancels_previous(self, bridge):
        bridge.scanForServers()
        bridge.scanForServers()
        assert len(bridge.discoveredServers) == 2


class TestManualConnection:
    def test_connect_manual_saves_settings(self, bridge):
        result = bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert result["ok"] is True

    def test_connect_manual_sets_alias(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert bridge.microServerAlias == "MyServer"

    def test_connect_manual_state_detected(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "")
        assert bridge.microServerState == "detected"

    def test_add_manual_server(self, bridge):
        result = bridge.addManualServer("10.0.0.1", 53318, "Manual")
        assert result["ok"] is True

    def test_add_manual_empty_host(self, bridge):
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_HOST"


class TestPairingAuth:
    def test_request_pair_changes_state(self, bridge):
        bridge.requestPair()
        assert bridge.microServerState == "pairing_required"

    def test_confirm_pair_connects(self, bridge):
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
        assert bridge.microServerState == "connected"

    def test_confirm_pair_sets_contact(self, bridge):
        bridge.requestPair()
        bridge.confirmPair()
        assert bridge.lastContact > 0

    def test_reject_pair_resets(self, bridge):
        bridge.requestPair()
        bridge.rejectPair()
        assert bridge.microServerState == "not_configured"

    def test_confirm_pair_sets_contract(self, bridge, mock_ctrl):
        bridge.requestPair()
        bridge.confirmPair()
        assert bridge.microServerContract == "contract_ok"


class TestDisconnectReconnect:
    def test_disconnect_resets_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
        assert bridge.microServerAlias == ""

    def test_disconnect_clears_error(self, bridge):
        bridge.disconnect()
        assert bridge.lastError == ""

    def test_forget_server_clears_all(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.forgetServer()
        assert bridge.microServerState == "not_configured"

    def test_reconnect_calls_controller(self, bridge, mock_ctrl):
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called


class TestDiagnostics:
    def test_diagnose_updates_state(self, bridge):
        result = bridge.diagnose()
        assert result["ok"] is True

    def test_diagnose_populates_version(self, bridge):
        bridge.diagnose()
        assert bridge.serverVersion == "Michi Server"

    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True


class TestCapabilities:
    def test_capabilities_populated_after_pair(self, bridge):
        bridge.requestPair()
        bridge.confirmPair()
        caps = bridge.capabilities
        assert len(caps) >= 4
        assert any(c["key"] == "can_continue_playback" and c["enabled"] for c in caps)

    @pytest.mark.parametrize("key,label", [
        ("can_continue_playback", "Continuar reproducción"),
        ("can_import", "Importar música"),
    ])
    def test_capability_labels(self, bridge, key, label):
        bridge.requestPair()
        bridge.confirmPair()
        caps = bridge.capabilities
        assert any(c["key"] == key and c["label"] == label for c in caps)


class TestIsolatedBridge:
    def test_no_controller_returns_ok_when_possible(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.microServerState == "not_configured"

    def test_no_controller_scan_handled(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.scanForServers()
        assert result["ok"] is True

    def test_no_controller_reconnect_handled(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_external_servers_empty(self, bridge):
        assert hasattr(bridge, "discoveredServers")
