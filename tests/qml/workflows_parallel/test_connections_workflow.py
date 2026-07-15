"""Workflow test: discover → connect → disconnect → reconnect → forget via ConnectionsBridge."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge

pytestmark = [pytest.mark.qml_module("connections"), pytest.mark.qml_workflow("connections")]


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    ctrl.discover_servers.return_value = [
        MagicMock(name="MichiServer", host="192.168.1.10"),
        MagicMock(name="OfficeServer", host="192.168.1.20"),
    ]
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
        "contract_ok": True,
        "can_continue_playback": True,
        "can_import": False,
        "can_send_genre_playlist": False,
        "can_send_genre_mix": False,
    }
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
    }
    ctrl.reconnect.return_value = {"ok": True}
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(michi_link_ctrl=mock_ctrl)


class TestConnectionsWorkflow:
    """Complete workflow: discover → connect → disconnect → reconnect → forget."""

    def test_wf_discover(self, bridge, mock_ctrl):
        result = bridge.scanForServers()
        assert result["ok"] is True
        assert result["count"] >= 2
        assert len(bridge.discoveredServers) >= 2
        assert bridge.microServerState == "connected"

    def test_wf_discover_empty(self, bridge, mock_ctrl):
        mock_ctrl.discover_servers.return_value = []
        result = bridge.scanForServers()
        assert result["ok"] is True
        assert result["count"] == 0

    def test_wf_discover_error(self, bridge, mock_ctrl):
        mock_ctrl.discover_servers.side_effect = RuntimeError("Network error")
        result = bridge.scanForServers()
        assert result["ok"] is False
        assert bridge.microServerState == "error"

    def test_wf_connect_manual(self, bridge):
        result = bridge.connectManual("192.168.1.100", 53318, "MyServer")
        assert result["ok"] is True
        assert bridge.microServerAlias == "MyServer"

    def test_wf_connect_manual_empty_host(self, bridge):
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_HOST"

    def test_wf_pair_request(self, bridge):
        result = bridge.requestPair()
        assert result["ok"] is True
        assert bridge.microServerState == "pairing_required"

    def test_wf_pair_confirm(self, bridge, mock_ctrl):
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
        assert bridge.microServerState == "connected"

    def test_wf_pair_reject(self, bridge):
        bridge.requestPair()
        result = bridge.rejectPair()
        assert result["ok"] is True
        assert bridge.microServerState == "not_configured"

    def test_wf_disconnect(self, bridge):
        bridge.connectManual("192.168.1.100", 53318, "MyServer")
        result = bridge.disconnect()
        assert result["ok"] is True
        assert bridge.microServerState == "not_configured"
        assert bridge.microServerAlias == ""

    def test_wf_reconnect(self, bridge, mock_ctrl):
        bridge.connectManual("192.168.1.100", 53318, "MyServer")
        bridge.disconnect()
        result = bridge.reconnect()
        assert result["ok"] is True
        assert bridge.microServerState == "connected"

    def test_wf_reconnect_no_ctrl(self):
        empty = ConnectionsBridge(michi_link_ctrl=None)
        result = empty.reconnect()
        assert result["ok"] is False

    def test_wf_forget_server(self, bridge, mock_ctrl):
        bridge.connectManual("192.168.1.100", 53318, "MyServer")
        result = bridge.forgetServer()
        assert result["ok"] is True
        assert bridge.microServerState == "not_configured"
        assert bridge.microServerAlias == ""

    def test_wf_diagnose(self, bridge, mock_ctrl):
        bridge.connectManual("192.168.1.100", 53318, "MyServer")
        result = bridge.diagnose()
        assert result["ok"] is True
        assert bridge.serverVersion == "MichiServer"

    def test_wf_diagnose_no_ctrl(self):
        empty = ConnectionsBridge(michi_link_ctrl=None)
        result = empty.diagnose()
        assert result["ok"] is True

    def test_wf_refresh_updates_state(self, bridge, mock_ctrl):
        result = bridge.refresh()
        assert result["ok"] is True
        assert bridge.microServerState == "connected"

    def test_wf_refresh_no_ctrl(self):
        empty = ConnectionsBridge(michi_link_ctrl=None)
        result = empty.refresh()
        assert result["ok"] is True
        assert empty.microServerState == "service_unavailable"

    def test_wf_capabilities_exposed(self, bridge, mock_ctrl):
        bridge.diagnose()
        caps = bridge.capabilities
        assert len(caps) >= 1
        can_continue = [c for c in caps if c["key"] == "can_continue_playback"]
        assert len(can_continue) == 1
        assert can_continue[0]["enabled"] is True

    def test_wf_navigate_home_audio(self, bridge):
        nav = MagicMock()
        nav.navigate.return_value = None
        bridge._nav_bridge = nav
        result = bridge.openHomeAudio("home_audio")
        assert result["ok"] is True
        nav.navigate.assert_called_once_with("home_audio")

    def test_wf_navigate_home_audio_no_nav(self, bridge):
        result = bridge.openHomeAudio("home_audio")
        assert result["ok"] is False

    def test_wf_full_cycle(self, bridge, mock_ctrl):
        result = bridge.scanForServers()
        assert result["ok"] is True
        bridge.connectManual("192.168.1.50", 53318, "FullCycle")
        assert bridge.microServerAlias == "FullCycle"
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
        bridge.reconnect()
        assert bridge.microServerState == "connected"
        bridge.forgetServer()
        assert bridge.microServerAlias == ""

    def test_wf_scan_after_disconnect(self, bridge, mock_ctrl):
        bridge.scanForServers()
        bridge.disconnect()
        result = bridge.scanForServers()
        assert result["ok"] is True
        assert result["count"] >= 2

    def test_wf_service_unavailable_init(self):
        empty = ConnectionsBridge(michi_link_ctrl=None)
        assert empty.microServerState == "service_unavailable"

    def test_wf_service_unavailable_scan(self):
        empty = ConnectionsBridge(michi_link_ctrl=None)
        result = empty.scanForServers()
        assert result["ok"] is False
        assert "SERVICE_UNAVAILABLE" in result["error"]

    def test_wf_add_manual_server(self, bridge):
        result = bridge.addManualServer("10.0.0.1", 53318, "Lab Server")
        assert result["ok"] is True
        assert bridge.microServerState == "detected"

    def test_wf_add_manual_server_no_alias(self, bridge):
        result = bridge.addManualServer("10.0.0.2", 53318)
        assert result["ok"] is True
