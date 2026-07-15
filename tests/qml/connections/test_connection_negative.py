<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test negative cases: missing service, failed connection, timeout."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Tests for connection negative cases: null bridge, errors, unavailable state."""
>>>>>>> Stashed changes
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


class TestNoController:
    def test_missing_service_state(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.microServerState == "not_configured"

    def test_missing_service_error_empty(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.lastError == ""

    def test_missing_service_scan(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.scanForServers()
        assert result["ok"] is True

    def test_missing_service_reconnect(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_missing_service_diagnose(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.diagnose()
        assert result["ok"] is True

    def test_missing_service_add_manual_empty(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_missing_service_confirm_pair(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True

    def test_missing_service_forget(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.forgetServer()
        assert result["ok"] is True

    def test_missing_service_disconnect(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.disconnect()
        assert result["ok"] is True

    def test_missing_service_latency_zero(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.latencyMs == 0


class TestFailedConnection:
    @pytest.fixture
    def failing_ctrl(self):
        ctrl = MagicMock()
        ctrl.discover_servers.side_effect = Exception("Network unreachable")
        ctrl.get_capabilities.side_effect = Exception("Service unavailable")
        ctrl.reconnect.side_effect = Exception("Connection refused")
        ctrl.get_connection_state.side_effect = Exception("No response")
        ctrl.is_connected = False
        return ctrl

    @pytest.fixture
    def bridge(self, failing_ctrl):
        return ConnectionsBridge(michi_link_ctrl=failing_ctrl)

    def test_scan_failure_error_state(self, bridge):
        result = bridge.scanForServers()
        assert result["ok"] is False

    def test_reconnect_failure(self, bridge):
        result = bridge.reconnect()
        assert result["ok"] is False

    def test_diagnose_failure(self, bridge):
        result = bridge.diagnose()
        assert result["ok"] is False

    def test_confirm_pair_failure(self, bridge):
        bridge.requestPair()
        result = bridge.confirmPair()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
"""Test negative cases: missing service, failed connection, timeout."""
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


class TestNoController:
    def test_missing_service_state(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.microServerState == "not_configured"

    def test_missing_service_error_empty(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.lastError == ""

    def test_missing_service_scan(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.scanForServers()
        assert result["ok"] is True

    def test_missing_service_reconnect(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_missing_service_diagnose(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.diagnose()
        assert result["ok"] is True

    def test_missing_service_add_manual_empty(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_missing_service_confirm_pair(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True

    def test_missing_service_forget(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.forgetServer()
        assert result["ok"] is True

    def test_missing_service_disconnect(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        result = b.disconnect()
        assert result["ok"] is True

    def test_missing_service_latency_zero(self):
        b = ConnectionsBridge(michi_link_ctrl=None)
        assert b.latencyMs == 0


class TestFailedConnection:
    @pytest.fixture
    def failing_ctrl(self):
        ctrl = MagicMock()
        ctrl.discover_servers.side_effect = Exception("Network unreachable")
        ctrl.get_capabilities.side_effect = Exception("Service unavailable")
        ctrl.reconnect.side_effect = Exception("Connection refused")
        ctrl.get_connection_state.side_effect = Exception("No response")
        ctrl.is_connected = False
        return ctrl

    @pytest.fixture
    def bridge(self, failing_ctrl):
        return ConnectionsBridge(michi_link_ctrl=failing_ctrl)

    def test_scan_failure_error_state(self, bridge):
        result = bridge.scanForServers()
        assert result["ok"] is False

    def test_reconnect_failure(self, bridge):
        result = bridge.reconnect()
        assert result["ok"] is False

    def test_diagnose_failure(self, bridge):
        result = bridge.diagnose()
        assert result["ok"] is False

    def test_confirm_pair_failure(self, bridge):
        bridge.requestPair()
        result = bridge.confirmPair()
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        assert result["ok"] is False

    def test_connect_manual_still_works(self, bridge):
        result = bridge.connectManual("10.0.0.1", 53318, "Failing")
        assert result["ok"] is True


class TestTimeout:
    @pytest.fixture
    def timeout_ctrl(self):
        ctrl = MagicMock()
        import time
        def slow_op():
            time.sleep(0.1)
            return []
        ctrl.discover_servers.side_effect = slow_op
        ctrl.get_capabilities.return_value = {
            "micro_server_state": "connected",
            "micro_server_name": "TimeoutServer",
            "contract_ok": False,
        }
        ctrl.reconnect.return_value = True
        ctrl.get_connection_state.return_value = {
            "micro_server_state": "connected",
            "micro_server_name": "TimeoutServer",
        }
        ctrl.is_connected = True
        return ctrl

    @pytest.fixture
    def bridge(self, timeout_ctrl):
        return ConnectionsBridge(michi_link_ctrl=timeout_ctrl)

    def test_scan_slow(self, bridge):
        result = bridge.scanForServers()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        assert result["ok"] is True
