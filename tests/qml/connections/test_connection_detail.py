"""Tests for ConnectionDetailPage QML component."""
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


class TestConnectionDetailPage:
    def test_file_exists(self, qml_dir):
        p = qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml"
        assert p.exists()

    def test_component_loads(self, engine, qml_dir):
        engine.addImportPath(str(qml_dir))
        component = QQmlComponent(engine)
        component.loadUrl(QUrl.fromLocalFile(str(qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml")))
        assert component.isReady()

    def test_has_objectName(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "objectName" in content
        assert "connectionDetailPage" in content

    def test_signals_declared(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "signal backClicked()" in content
        assert "signal reconnectClicked()" in content
        assert "signal disconnectClicked()" in content
        assert "signal forgetServerClicked()" in content
        assert "signal editClicked()" in content

    def test_action_buttons_exist(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "Reconectar" in content
        assert "Desconectar" in content
        assert "Editar" in content
        assert "Olvidar servidor" in content

    def test_all_buttons_have_onClicked(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        for method in ["reconnectClicked", "disconnectClicked", "editClicked", "forgetServerClicked", "backClicked"]:
            assert "onClicked: root." + method in content, f"Button missing onClicked for {method}"

    def test_has_accessible(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_has_status_card(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "GlassCard" in content
        assert "Estado" in content

    def test_has_capabilities_panel(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "ConnectionCapabilities" in content

    def test_has_error_panel(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "ConnectionErrorPanel" in content

    def test_has_back_button(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "Volver" in content


class TestConnectionDetailBridge:
    def test_state_properties(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        assert hasattr(bridge, 'microServerState')
        assert hasattr(bridge, 'lastError')
        assert hasattr(bridge, 'latencyMs')
        assert hasattr(bridge, 'serverVersion')

    def test_capabilities_property(self):
        bridge = ConnectionsBridge(michi_link_ctrl=None)
        caps = bridge.capabilities
        assert isinstance(caps, list)

    def test_disconnect(self, mock_ctrl):
        ctrl = MagicMock()
        bridge = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = bridge.disconnect()
        assert result["ok"] is True

    def test_forget_server(self):
        ctrl = MagicMock()
        bridge = ConnectionsBridge(michi_link_ctrl=ctrl)
        result = bridge.forgetServer()
        assert result["ok"] is True
