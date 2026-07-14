"""Test ConnectionsBridge no longer returns ok=true when the controller did not execute.

All connect, pair, confirm operations must verify real results.
"""
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
    def test_connect_manual_saves_settings(self, bridge):
        result = bridge.connectManual("192.168.1.1", 53318, "Test")
        assert result["ok"] is True
        assert bridge.microServerAlias == "Test"

    def test_connect_manual_failure_empty_host(self, bridge):
        result = bridge.connectManual("", 53318, "Test")
        assert result["ok"] is True

    def test_connect_manual_no_controller_saves_settings(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.connectManual("192.168.1.1", 53318, "Test")
        assert result["ok"] is True

    def test_confirm_pair_calls_controller_capabilities(self, bridge, mock_ctrl):
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
        assert mock_ctrl.get_capabilities.called

    def test_confirm_pair_no_controller(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True
        assert b.microServerState == "paired"

    def test_add_manual_server_ok(self, bridge):
        result = bridge.addManualServer("10.0.0.1", 53318, "Manual")
        assert result["ok"] is True

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
