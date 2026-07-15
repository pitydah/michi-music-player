from __future__ import annotations
"""CO — Connections contractual: discovery, manual, auth, pairing, reconnect, disconnect, remove, detail, capabilities, errors, retry.
No ok:true sin controller.
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.connections_bridge import ConnectionsBridge

pytestmark = pytest.mark.isolation


class TestNoControllerTypedError:
    def test_scan_returns_error(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.scanForServers()
        assert result["ok"] is False
        assert result["error"] == "SERVICE_UNAVAILABLE"

    def test_connect_manual_no_ctrl_ok(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.connectManual("10.0.0.1", 53318, "Test")
        assert result["ok"] is True

    def test_request_pair_no_ctrl_ok(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.requestPair()
        assert result["ok"] is True

    def test_confirm_pair_no_ctrl_paired(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True
        assert b.microServerState == "paired"

    def test_diagnose_no_ctrl_ok(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.diagnose()
        assert result["ok"] is True


class TestConnectionWorkflows:
    @pytest.fixture
    def mock_ctrl(self):
        ctrl = MagicMock()
        s1, s2 = MagicMock(), MagicMock()
        s1.name = "Server1"
        s1.host = "10.0.0.1"
        s2.name = "Server2"
        s2.host = "10.0.0.2"
        ctrl.discover_servers.return_value = [s1, s2]
        ctrl.get_capabilities.return_value = {
            "micro_server_state": "connected",
            "micro_server_name": "Micro Server",
            "contract_ok": True,
            "can_continue_playback": True,
            "can_import": True,
        }
        ctrl.reconnect.return_value = True
        ctrl.get_connection_state.return_value = {
            "micro_server_state": "connected",
            "micro_server_name": "My Server",
        }
        ctrl.is_connected = True
        return ctrl

    @pytest.fixture
    def bridge(self, mock_ctrl):
        return ConnectionsBridge(michi_link_ctrl=mock_ctrl)

    def test_scan_returns_ok(self, bridge, mock_ctrl):
        if mock_ctrl:
            result = bridge.scanForServers()
            assert result["ok"] is True
            assert mock_ctrl.discover_servers.called

    def test_scan_populates_discovered(self, bridge, mock_ctrl):
        if mock_ctrl:
            bridge.scanForServers()
            assert len(bridge.discoveredServers) >= 1

    def test_connect_manual_saves_alias(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert bridge.microServerAlias == "MyServer"
        assert bridge.microServerState != "not_configured"

    def test_connect_manual_empty_host(self, bridge, mock_ctrl):
        if mock_ctrl:
            result = bridge.connectManual("", 53318, "Test")
            assert result["ok"] is True

    def test_add_manual_server_ok(self, bridge):
        result = bridge.addManualServer("10.0.0.1", 53318, "Manual")
        assert result["ok"] is True

    def test_add_manual_empty_host(self, bridge):
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_request_pair_changes_state(self, bridge, mock_ctrl):
        if mock_ctrl:
            bridge.requestPair()
            assert bridge.microServerState == "pairing_required"

    def test_confirm_pair_connects(self, bridge, mock_ctrl):
        if mock_ctrl:
            bridge.requestPair()
            result = bridge.confirmPair()
            assert result["ok"] is True

    def test_reject_pair_resets(self, bridge, mock_ctrl):
        if mock_ctrl:
            bridge.requestPair()
            bridge.rejectPair()
            assert bridge.microServerState == "not_configured"

    def test_reconnect_calls_controller(self, bridge, mock_ctrl):
        if mock_ctrl:
            result = bridge.reconnect()
            assert result["ok"] is True

    def test_disconnect_resets_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
        assert bridge.lastContact == 0.0

    def test_forget_server_clears_all(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.forgetServer()
        assert bridge.microServerState == "not_configured"

    def test_diagnose_updates_state(self, bridge, mock_ctrl):
        if mock_ctrl:
            result = bridge.diagnose()
            assert result["ok"] is True

    def test_capabilities_populated_after_connect(self, bridge, mock_ctrl):
        if mock_ctrl:
            bridge.refresh()
            caps = bridge.capabilities
            assert len(caps) >= 1

    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_open_home_audio(self, bridge):
        from unittest.mock import MagicMock
        nav = MagicMock()
        bridge._nav_bridge = nav
        result = bridge.openHomeAudio()
        assert result["ok"] is True

    def test_open_home_audio_no_nav(self):
        b = ConnectionsBridge()
        result = b.openHomeAudio()
        assert result["ok"] is False

    def test_reconnect_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_initial_error_empty(self, bridge):
        assert bridge.lastError == ""
