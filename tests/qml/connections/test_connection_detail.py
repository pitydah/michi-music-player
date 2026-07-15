"""Test Connection detail page behavior with mock connection."""
"""Tests for ConnectionDetailPage QML component."""
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


class TestDetailState:
    def test_connected_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "DetailServer")
        assert bridge.microServerState == "detected"

    def test_alias_populated(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "DetailServer")
        assert bridge.microServerAlias == "DetailServer"

    def test_latency_ms_default(self, bridge):
        assert bridge.latencyMs == 0

    def test_last_contact_initially_zero(self, bridge):
        assert bridge.lastContact == 0.0

    def test_capabilities_structure(self, bridge):
        bridge.diagnose()
        caps = bridge.capabilities
        assert isinstance(caps, list)

    def test_contract_after_connect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "S")
        assert bridge.microServerContract == ""

    def test_external_servers_empty(self, bridge):
        assert bridge.externalServers == []

    def test_property_default(self, bridge):
        assert bridge.protocol == "michi-link"

    def test_compatible_default(self, bridge):
        assert bridge.compatible is False

    def test_compatible_after_connect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "S")
        assert bridge.compatible is False


class TestDetailActions:
    def test_disconnect_clears_alias(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.disconnect()
        assert bridge.microServerAlias == ""

    def test_disconnect_clears_error(self, bridge):
        bridge.disconnect()
        assert bridge.lastError == ""

    def test_forget_resets_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.forgetServer()
        assert bridge.microServerState == "not_configured"

    def test_reconnect_calls_ctrl(self, bridge, mock_ctrl):
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called

    def test_diagnose_updates_version(self, bridge):
        bridge.diagnose()
        assert bridge.serverVersion == "Michi Server"

    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_forget_server(self):
        ctrl = MagicMock()
        bridge = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = bridge.forgetServer()
        assert result["ok"] is True
"""Test Connection detail page behavior with mock connection."""

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


class TestDetailState:
    def test_connected_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "DetailServer")
        assert bridge.microServerState == "detected"

    def test_alias_populated(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "DetailServer")
        assert bridge.microServerAlias == "DetailServer"

    def test_latency_ms_default(self, bridge):
        assert bridge.latencyMs == 0

    def test_last_contact_initially_zero(self, bridge):
        assert bridge.lastContact == 0.0

    def test_capabilities_structure(self, bridge):
        bridge.diagnose()
        caps = bridge.capabilities
        assert isinstance(caps, list)

    def test_contract_after_connect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "S")
        assert bridge.microServerContract == ""

    def test_external_servers_empty(self, bridge):
        assert bridge.externalServers == []

    def test_property_default(self, bridge):
        assert bridge.protocol == "michi-link"

    def test_compatible_default(self, bridge):
        assert bridge.compatible is False

    def test_compatible_after_connect(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "S")
        assert bridge.compatible is False


class TestDetailActions:
    def test_disconnect_clears_alias(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.disconnect()
        assert bridge.microServerAlias == ""

    def test_disconnect_clears_error(self, bridge):
        bridge.disconnect()
        assert bridge.lastError == ""

    def test_forget_resets_state(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.forgetServer()
        assert bridge.microServerState == "not_configured"

    def test_reconnect_calls_ctrl(self, bridge, mock_ctrl):
        result = bridge.reconnect()
        assert result["ok"] is True
        assert mock_ctrl.reconnect.called

    def test_diagnose_updates_version(self, bridge):
        bridge.diagnose()
        assert bridge.serverVersion == "Michi Server"

    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_scan_populates_discovered(self, bridge):
        bridge.scanForServers()
        assert len(bridge.discoveredServers) >= 1


class TestDetailNoController:
    def test_state_not_configured(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.microServerState == "not_configured"

    def test_scan_empty(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.scanForServers()
        assert b.discoveredServers == []

    def test_reconnect_fails(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False
