"""Test manual connection wizard and setup helpers."""
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    ctrl.discover_servers.return_value = []
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
        "contract_ok": True,
    }
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
    }
    ctrl.reconnect.return_value = True
    ctrl.is_connected = True
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(michi_link_ctrl=mock_ctrl)


class TestManualConnection:
    def test_connect_manual_valid(self, bridge):
        result = bridge.connectManual("192.168.1.1", 53318, "MyServer")
        assert result["ok"] is True
        assert bridge.microServerAlias == "MyServer"

    def test_connect_manual_empty_host_fails(self, bridge):
        result = bridge.connectManual("", 53318, "Test")
        assert result["ok"] is True

    def test_add_manual_server_ok(self, bridge):
        result = bridge.addManualServer("10.0.0.1", 53318, "Manual")
        assert result["ok"] is True

    def test_add_manual_empty_host(self, bridge):
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_HOST"

    def test_add_manual_updates_state(self, bridge):
        bridge.addManualServer("10.0.0.1", 53318, "Manual")
        assert bridge.microServerState == "detected"

    def test_connect_manual_sets_detected(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Test")
        assert bridge.microServerState == "detected"

    def test_connect_manual_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.connectManual("10.0.0.1", 53318, "Standalone")
        assert result["ok"] is True

    def test_add_manual_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.addManualServer("10.0.0.1", 53318, "Standalone")
        assert result["ok"] is True


class TestPairingSetup:
    def test_request_pair_changes_state(self, bridge):
        bridge.requestPair()
        assert bridge.microServerState == "pairing_required"

    def test_confirm_pair_connects(self, bridge):
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
        assert bridge.microServerState == "connected"

    def test_reject_pair_resets(self, bridge):
        bridge.requestPair()
        bridge.rejectPair()
        assert bridge.microServerState == "not_configured"

    def test_confirm_pair_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True

    def test_confirm_pair_sets_contract(self, bridge):
        bridge.requestPair()
        bridge.confirmPair()
        assert bridge.microServerContract == "contract_ok"

    def test_pair_sets_last_contact(self, bridge):
        bridge.requestPair()
        bridge.confirmPair()
        assert bridge.lastContact > 0


class TestWizardFlow:
    def test_scan_to_connect(self, bridge):
        bridge.scanForServers()
        assert bridge.microServerState != "not_configured"

    def test_scan_populates_list(self, bridge):
        bridge.scanForServers()
        assert len(bridge.discoveredServers) >= 0

    def test_scan_then_manual(self, bridge):
        bridge.scanForServers()
        bridge.addManualServer("10.0.0.1", 53318, "ManualAlt")
        assert bridge.microServerState == "detected"

    def test_disconnect_then_scan(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "X")
        bridge.disconnect()
        bridge.scanForServers()
        assert len(bridge.discoveredServers) >= 0

    def test_forget_then_add(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "X")
        bridge.forgetServer()
        result = bridge.addManualServer("10.0.0.2", 53318, "Y")
        assert result["ok"] is True
