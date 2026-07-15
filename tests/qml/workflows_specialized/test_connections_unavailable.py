"""MM: Test ConnectionsBridge — UNAVAILABLE state, no bridge = no false ok."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge


@pytest.fixture
def bridge_no_ctrl():
    return ConnectionsBridge(michi_link_ctrl=None)


@pytest.fixture
def bridge_with_ctrl():
    ctrl = MagicMock()
    ctrl.discover_servers.return_value = []
    ctrl.reconnect.return_value = {"ok": False, "error": "UNREACHABLE"}
    return ConnectionsBridge(michi_link_ctrl=ctrl)


class TestConnectionsUnavailable:
    def test_no_ctrl_returns_not_configured(self, bridge_no_ctrl):
        assert bridge_no_ctrl.microServerState == "not_configured"

    def test_no_ctrl_scan_returns_ok_zero_count(self, bridge_no_ctrl):
        result = bridge_no_ctrl.scanForServers()
        assert result.get("ok") is True
        assert result.get("count") == 0

    def test_no_ctrl_discovered_is_empty(self, bridge_no_ctrl):
        assert bridge_no_ctrl.discoveredServers == []

    def test_no_ctrl_compatible_is_false(self, bridge_no_ctrl):
        assert bridge_no_ctrl.compatible is False

    def test_no_ctrl_latency_is_zero(self, bridge_no_ctrl):
        assert bridge_no_ctrl.latencyMs == 0

    def test_no_ctrl_last_contact_is_zero(self, bridge_no_ctrl):
        assert bridge_no_ctrl.lastContact == 0.0

    def test_no_ctrl_external_servers_is_empty(self, bridge_no_ctrl):
        assert bridge_no_ctrl.externalServers == []

    def test_no_ctrl_disconnect_does_not_raise(self, bridge_no_ctrl):
        try:
            bridge_no_ctrl.disconnect()
        except Exception:
            pytest.fail("disconnect raised without controller")

    def test_no_ctrl_forget_server_does_not_raise(self, bridge_no_ctrl):
        try:
            bridge_no_ctrl.forgetServer()
        except Exception:
            pytest.fail("forgetServer raised without controller")

    def test_no_ctrl_refresh_keeps_not_configured(self, bridge_no_ctrl):
        bridge_no_ctrl.refresh()
        assert bridge_no_ctrl.microServerState == "not_configured"

    def test_no_ctrl_reconnect_returns_unsupported(self, bridge_no_ctrl):
        result = bridge_no_ctrl.reconnect()
        assert result.get("error") == "UNSUPPORTED"

    def test_no_ctrl_diagnose_returns_no_error(self, bridge_no_ctrl):
        result = bridge_no_ctrl.diagnose()
        assert result.get("ok") is True

    def test_no_ctrl_confirm_pair_returns_ok(self, bridge_no_ctrl):
        result = bridge_no_ctrl.confirmPair()
        assert result.get("ok") is True

    def test_no_ctrl_reject_pair_sets_not_configured(self, bridge_no_ctrl):
        bridge_no_ctrl.rejectPair()
        assert bridge_no_ctrl.microServerState == "not_configured"

    def test_no_ctrl_add_manual_returns_error_on_empty(self, bridge_no_ctrl):
        result = bridge_no_ctrl.addManualServer(host="")
        assert result.get("error") == "EMPTY_HOST"

    def test_no_ctrl_with_host_changes_state(self, bridge_no_ctrl):
        result = bridge_no_ctrl.addManualServer(host="192.168.1.10", port=53318, alias="Test")
        assert result.get("ok") is True
        assert bridge_no_ctrl.microServerState == "detected"

    def test_no_ctrl_reconnect_fails_with_message(self, bridge_no_ctrl):
        result = bridge_no_ctrl.reconnect()
        assert not result.get("ok", True)

    def test_no_ctrl_scan_does_not_blow_up(self, bridge_no_ctrl):
        try:
            bridge_no_ctrl.scanForServers()
        except Exception:
            pytest.fail("scanForServers raised without controller")

    def test_ctrl_reconnect_failure_no_false_ok(self, bridge_with_ctrl):
        result = bridge_with_ctrl.reconnect()
        assert not result.get("ok", True)
