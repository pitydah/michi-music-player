"""Test ConnectionsBridge no longer returns ok=true when the controller did not execute.

All connect, pair, confirm operations must verify real results.
"""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.connections_bridge import ConnectionsBridge


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    ctrl.discover_servers.return_value = []
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
        "contract_ok": True,
        "can_continue_playback": True,
        "can_import": False,
        "can_send_genre_playlist": True,
        "can_send_genre_mix": False,
    }
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "connected",
        "micro_server_name": "MichiServer",
    }
    ctrl.reconnect.return_value = True
    ctrl.is_connected = True
    ctrl.connect = MagicMock(return_value={"ok": True})
    ctrl.pair = MagicMock(return_value={"ok": True})
    ctrl.test_connection = MagicMock(return_value=True)
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(michi_link_ctrl=mock_ctrl)


class TestConnectNoFalseOk:
    def test_connect_manual_calls_controller(self, bridge, mock_ctrl):
        result = bridge.connectManual("192.168.1.1", 53318, "Test")
        assert result["ok"] is True
        assert mock_ctrl.connect.called or mock_ctrl.test_connection.called

    def test_connect_manual_failure_propagates(self):
        ctrl = MagicMock()
        ctrl.connect = MagicMock(return_value={"ok": False, "error": "REFUSED"})
        ctrl.test_connection = MagicMock(return_value=False)
        b = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = b.connectManual("192.168.1.1", 53318, "Test")
        assert result["ok"] is False

    def test_connect_manual_no_controller_saves_settings(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.connectManual("192.168.1.1", 53318, "Test")
        assert result["ok"] is True  # settings saved even without live controller
        assert b.microServerState == "connected"

    def test_confirm_pair_calls_controller_pair(self, bridge, mock_ctrl):
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
        assert mock_ctrl.pair.called or mock_ctrl.get_capabilities.called

    def test_confirm_pair_failure_when_no_capabilities(self):
        ctrl = MagicMock()
        ctrl.pair = MagicMock(return_value={"ok": True})
        ctrl.get_capabilities = MagicMock(return_value={})
        b = ConnectionsBridge(michi_link_ctrl=ctrl)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is False

    def test_confirm_pair_failure_when_pair_returns_false(self):
        ctrl = MagicMock()
        ctrl.pair = MagicMock(return_value={"ok": False, "error": "AUTH_FAILED"})
        ctrl.get_capabilities = MagicMock(return_value={"contract_ok": False})
        b = ConnectionsBridge(michi_link_ctrl=ctrl)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is False

    def test_confirm_pair_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is False

    def test_add_manual_server_verifies_connection(self, mock_ctrl):
        result = ConnectionsBridge(michi_link_ctrl=mock_ctrl).addManualServer(
            "10.0.0.1", 53318, "Manual")
        assert result["ok"] is True
        assert mock_ctrl.test_connection.called

    def test_add_manual_server_failure(self):
        ctrl = MagicMock()
        ctrl.test_connection = MagicMock(return_value=False)
        b = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = b.addManualServer("10.0.0.1", 53318, "Manual")
        assert result["ok"] is False

    def test_add_manual_server_empty_host(self, bridge):
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_reconnect_calls_controller(self, bridge, mock_ctrl):
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called

    def test_reconnect_failure_when_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False
