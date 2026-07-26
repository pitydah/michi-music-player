"""Tests for ConnectionsPage QML - states and actions."""
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from ui_qml_bridge.connections_bridge import ConnectionsBridge

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
    ctrl.discover.return_value = []
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
        assert "connectionsPage_control" in content

    def test_has_states(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "stateLoading" in content
        assert "stateReady" in content
        assert "stateError" in content
        assert "stateEmpty" in content

    def test_has_focusScope(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "focus: true" in content

    def test_has_accessible(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "Accessible" in content

    def test_page_state_unavailable_without_bridge(self):
        bridge = ConnectionsBridge(connection_service=None)
        assert bridge.microServerState == "service_unavailable"

    def test_page_state_configured_with_bridge(self, mock_ctrl):
        bridge = ConnectionsBridge(connection_service=mock_ctrl)
        assert bridge.microServerState == "not_configured"

    def test_scan_servers(self, mock_ctrl):
        bridge = ConnectionsBridge(connection_service=mock_ctrl)
        result = bridge.scanForServers()
        assert result["ok"] is True

    def test_disconnect_resets_state(self, mock_ctrl):
        bridge = ConnectionsBridge(connection_service=mock_ctrl)
        bridge.connectManual("10.0.0.1", 53318, "Test")
        bridge.disconnect()
        assert bridge.microServerState == "not_configured"
