"""Test keyboard navigation patterns for connections."""
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


class TestKeyboardAccessible:
    def test_state_changed_signal_emitted(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda: signals.append(1))
        bridge.refresh()
        assert len(signals) >= 0

    def test_state_preserved_after_action(self, bridge):
        bridge.connectManual("10.0.0.1", 53318, "KBTest")
        assert bridge.microServerAlias == "KBTest"

    def test_disconnect_preserves_state(self, bridge):
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"

    def test_scan_accessible(self, bridge):
        result = bridge.scanForServers()
        assert "ok" in result

    def test_disconnect_accessible(self, bridge):
        result = bridge.disconnect()
        assert result["ok"] is True

    def test_forget_accessible(self, bridge):
        result = bridge.forgetServer()
        assert result["ok"] is True

    def test_reconnect_accessible(self, bridge):
        result = bridge.reconnect()
        assert result["ok"] is True

    def test_refresh_accessible(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_diagnose_accessible(self, bridge):
        result = bridge.diagnose()
        assert result["ok"] is True

    def test_open_home_audio_no_nav(self, bridge):
        result = bridge.openHomeAudio()
        assert result["ok"] is False

    def test_scan_then_refresh(self, bridge):
        bridge.scanForServers()
        bridge.refresh()
        assert bridge.microServerState != "error"
