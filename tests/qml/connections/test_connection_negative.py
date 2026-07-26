"""Test negative cases: missing service, failed connection, timeout."""
"""Tests for connection negative cases: null bridge, errors, unavailable state."""
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


class TestNoController:
    def test_missing_service_state(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.microServerState == "service_unavailable"

    def test_missing_service_error_empty(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.lastError == ""

    def test_missing_service_scan(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.scanForServers()
        assert result["ok"] is False

    def test_missing_service_reconnect(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_missing_service_diagnose(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.diagnose()
        assert result["ok"] is True

    def test_missing_service_add_manual_empty(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_missing_service_confirm_pair(self):
        b = ConnectionsBridge(connection_service=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True

    def test_missing_service_forget(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.forgetServer()
        assert result["ok"] is True

    def test_missing_service_disconnect(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.disconnect()
        assert result["ok"] is True

    def test_missing_service_latency_zero(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.latencyMs == 0


class TestFailedConnection:
    @pytest.fixture
    def failing_ctrl(self):
        ctrl = MagicMock()
        ctrl.discover.side_effect = Exception("Network unreachable")
        ctrl.reconnect.side_effect = Exception("Connection refused")
        ctrl.confirm_pair.side_effect = Exception("Pairing failed")
        ctrl.diagnose.side_effect = Exception("Diagnostics failed")
        return ctrl

    @pytest.fixture
    def bridge(self, failing_ctrl):
        return ConnectionsBridge(connection_service=failing_ctrl)

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
        assert result["ok"] is False
"""Test negative cases: missing service, failed connection, timeout."""

import pytest
pytestmark = pytest.mark.isolation


class TestNoController:
    def test_missing_service_state(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.microServerState == "service_unavailable"

    def test_missing_service_error_empty(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.lastError == ""

    def test_missing_service_scan(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.scanForServers()
        assert result["ok"] is False

    def test_missing_service_reconnect(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.reconnect()
        assert result["ok"] is False

    def test_missing_service_diagnose(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.diagnose()
        assert result["ok"] is True

    def test_missing_service_add_manual_empty(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.addManualServer("", 0, "")
        assert result["ok"] is False

    def test_missing_service_confirm_pair(self):
        b = ConnectionsBridge(connection_service=None)
        b.requestPair()
        result = b.confirmPair()
        assert result["ok"] is True

    def test_missing_service_forget(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.forgetServer()
        assert result["ok"] is True

    def test_missing_service_disconnect(self):
        b = ConnectionsBridge(connection_service=None)
        result = b.disconnect()
        assert result["ok"] is True

    def test_missing_service_latency_zero(self):
        b = ConnectionsBridge(connection_service=None)
        assert b.latencyMs == 0


class TestFailedConnection:
    @pytest.fixture
    def failing_ctrl(self):
        ctrl = MagicMock()
        ctrl.discover.side_effect = Exception("Network unreachable")
        ctrl.reconnect.side_effect = Exception("Connection refused")
        ctrl.confirm_pair.side_effect = Exception("Pairing failed")
        ctrl.diagnose.side_effect = Exception("Diagnostics failed")
        return ctrl


    @pytest.fixture
    def bridge(self, failing_ctrl):
        return ConnectionsBridge(connection_service=failing_ctrl)

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
        ctrl.discover.side_effect = slow_op
        ctrl.reconnect.return_value = True
        return ctrl

    @pytest.fixture
    def bridge(self, timeout_ctrl):
        return ConnectionsBridge(connection_service=timeout_ctrl)

    def test_scan_slow(self, bridge):
        result = bridge.scanForServers()
        assert result["ok"] is True
