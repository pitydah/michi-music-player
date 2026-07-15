"""Tests for ConnectionsPage QML - states and actions."""
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from ui_qml_bridge.connections_bridge import ConnectionsBridge

QML_DIR = None


@pytest.fixture(scope="module")
def qml_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    ctrl.discover_servers.return_value = []
    ctrl.get_capabilities.return_value = {
        "micro_server_state": "not_configured",
        "micro_server_name": "Michi Micro Server",
        "contract_ok": False,
        "can_continue_playback": True,
        "can_import": False,
        "can_send_genre_playlist": True,
        "can_send_genre_mix": False,
    }
    ctrl.get_connection_state.return_value = {
        "micro_server_state": "not_configured",
        "micro_server_name": "",
    }
    ctrl.reconnect.return_value = True
    return ctrl


class TestConnectionsPage:
    def test_page_file_exists(self, qml_dir):
        p = qml_dir / "pages" / "connections" / "ConnectionsPage.qml"
        assert p.exists()

    def test_component_loads(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "pages" / "connections" / "ConnectionsPage.qml")))
        assert component.isReady()

    def test_has_objectName(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "objectName" in content
        assert "connections.page" in content

    def test_has_states(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "AsyncStateView" in content
        assert "LOADING" in content
        assert "READY" in content
        assert "EMPTY" in content
        assert "ERROR" in content
        assert "UNAVAILABLE" in content

    def test_has_focusScope(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "FocusScope" in content

    def test_has_accessible(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "Accessible" in content

    def test_page_state_unavailable_without_bridge(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        assert bridge.microServerState == "service_unavailable"

    def test_page_state_configured_with_bridge(self, mock_ctrl):
        bridge = ConnectionsBridge(michi_link_ctrl=mock_ctrl)
        assert bridge.microServerState == "not_configured"

    def test_scan_servers(self, mock_ctrl):
        bridge = ConnectionsBridge(michi_link_ctrl=mock_ctrl)
        result = bridge.scanForServers()
        assert result["ok"] is True

    def test_disconnect_resets_state(self, mock_ctrl):
        bridge = ConnectionsBridge(michi_link_ctrl=mock_ctrl)
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
