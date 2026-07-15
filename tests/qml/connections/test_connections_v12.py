"""Tests for Connections v12 — operaciones async en ConnectionService.
Bridge solo refleja estado/errores."""
from unittest.mock import MagicMock



class TestConnectionsBridgeCreation:
    def test_creation(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge()
        assert cb is not None

    def test_initial_state(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge()
        assert cb.microServerState == "service_unavailable"

    def test_with_controller(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        assert cb.microServerState != "service_unavailable"

    def test_protocol(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge()
        assert cb.protocol == "michi-link"


class TestConnectionsOperations:
    def test_scan_no_controller(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge()
        result = cb.scanForServers()
        assert not result.get("ok")

    def test_refresh(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.refresh()
        assert result.get("ok")

    def test_disconnect(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.disconnect()
        assert result.get("ok")
        assert cb.microServerState == "not_configured"

    def test_forget_server(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.forgetServer()
        assert result.get("ok")

    def test_request_pair(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.requestPair()
        assert result.get("ok")

    def test_confirm_pair(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        ctrl = MagicMock()
        ctrl.get_capabilities.return_value = {"contract_ok": True}
        cb = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = cb.confirmPair()
        assert isinstance(result, dict)

    def test_reject_pair(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.rejectPair()
        assert result.get("ok")

    def test_diagnose(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        ctrl = MagicMock()
        ctrl.get_connection_state.return_value = {"micro_server_state": "connected"}
        ctrl.get_capabilities.return_value = {}
        cb = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = cb.diagnose()
        assert result.get("ok")

    def test_add_manual_server(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.addManualServer(host="192.168.1.100", port=53318, alias="Server")
        assert result.get("ok")

    def test_connect_manual(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        result = cb.connectManual("192.168.1.100", 53318, "Server")
        assert result.get("ok")

    def test_compatible(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock())
        assert isinstance(cb.compatible, bool)

    def test_open_home_audio(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        nav = MagicMock()
        nav.navigate = MagicMock(return_value={"ok": True})
        cb = ConnectionsBridge(michi_link_ctrl=MagicMock(), navigation_bridge=nav)
        result = cb.openHomeAudio()
        assert result.get("ok")
