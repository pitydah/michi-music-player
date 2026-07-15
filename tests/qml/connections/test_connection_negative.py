"""Tests for connection negative cases: null bridge, errors, unavailable state."""
from unittest.mock import MagicMock


from ui_qml_bridge.connections_bridge import ConnectionsBridge


class TestNullBridge:
    def test_service_unavailable_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        assert bridge.microServerState == "service_unavailable"

    def test_scan_fails_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.scanForServers()
        assert result["ok"] is False
        assert result["error"] == "SERVICE_UNAVAILABLE"

    def test_reconnect_fails_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.reconnect()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_diagnose_succeeds_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.diagnose()
        assert result["ok"] is True

    def test_disconnect_succeeds_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.disconnect()
        assert result["ok"] is True

    def test_capabilities_empty_without_ctrl(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        caps = bridge.capabilities
        assert isinstance(caps, list)
        assert all(c["enabled"] is False for c in caps)

    def test_state_changed_signal_emitted_on_error(self):
        ctrl = MagicMock()
        ctrl.discover_servers.side_effect = RuntimeError("Network error")
        bridge = ConnectionsBridge(michi_link_ctrl=ctrl)
        handler = MagicMock()
        bridge.stateChanged.connect(handler)
        result = bridge.scanForServers()
        assert result["ok"] is False
        assert "error" in result

    def test_last_error_cleared_on_disconnect(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        bridge._last_error = "Previous error"
        bridge.disconnect()
        assert bridge.lastError == ""

    def test_latency_reset_on_disconnect(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        bridge._latency_ms = 50
        bridge.disconnect()
        assert bridge.latencyMs == 0


class TestConnectionErrors:
    def test_add_manual_empty_host(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.addManualServer("", 0, "")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_HOST"

    def test_add_manual_with_host(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        result = bridge.addManualServer("10.0.0.1", 53318, "Test")
        assert result["ok"] is True

    def test_forget_server_clears_alias(self):
        bridge = ConnectionsBridge(michi_link_ctrl=MagicMock())
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        bridge.forgetServer()
        assert bridge.microServerAlias == ""

    def test_connect_manual_saves_alias(self):
        bridge = ConnectionsBridge(michi_link_ctrl=MagicMock())
        bridge.connectManual("10.0.0.1", 53318, "MyServer")
        assert bridge.microServerAlias == "MyServer"

    def test_open_home_audio_no_navigation(self):
        bridge = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = bridge.openHomeAudio("home_audio")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_pair_reject_resets_to_not_configured(self):
        bridge = ConnectionsBridge(michi_link_ctrl=MagicMock())
        bridge.requestPair()
        bridge.rejectPair()
        assert bridge.microServerState == "not_configured"

    def test_confirm_pair_without_capabilities(self):
        bridge = ConnectionsBridge(michi_link_ctrl=MagicMock())
        bridge.requestPair()
        result = bridge.confirmPair()
        assert result["ok"] is True
