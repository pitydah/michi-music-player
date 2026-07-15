"""Tests for keyboard navigation in connection components."""
import pytest
from PySide6.QtQml import QQmlEngine

QML_DIR = None


@pytest.fixture(scope="module")
def qml_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestConnectionKeyboard:
    def test_connections_page_keyboard_nav(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "KeyNavigation.tab" in content or "KeyNavigation" in content

    def test_connections_page_escape_handler(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "Keys.onEscapePressed" in content

    def test_connections_page_focus_scope(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionsPage.qml").read_text()
        assert "FocusScope" in content
        assert "activeFocusOnTab" in content

    def test_micro_server_hero_keyboard_nav(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "MicroServerHero.qml").read_text()
        assert "KeyNavigation" in content or "focusPolicy" in content or "activeFocusOnTab" in content

    def test_connection_detail_has_focusable_buttons(self, qml_dir):
        content = (qml_dir / "pages" / "connections" / "ConnectionDetailPage.qml").read_text()
        assert "MichiButton" in content

    def test_manual_dialog_keyboard_support(self, qml_dir):
        p = qml_dir / "pages" / "connections" / "ManualConnectionDialog.qml"
        content = p.read_text()
        assert "Keys" in content or "Escape" in content or "KeyNavigation" in content or "closePolicy" in content

    def test_all_cards_have_mousearea_click(self, qml_dir):
        for name in ["ConnectionCard.qml", "ConfiguredServerCard.qml", "DiscoveredServerCard.qml", "ExternalServerCard.qml"]:
            content = (qml_dir / "pages" / "connections" / name).read_text()
            assert "onClicked" in content

    def test_accessible_on_all_connection_pages(self, qml_dir):
        files = [
            "ConnectionsPage.qml", "ConnectionDetailPage.qml", "MicroServerHero.qml",
            "ConnectionCard.qml", "ConfiguredServerCard.qml", "DiscoveredServerCard.qml",
            "ExternalServerCard.qml", "ManualConnectionDialog.qml",
            "ConnectionCapabilities.qml", "ConnectionErrorPanel.qml",
            "NetworkDiscoveryPanel.qml", "ServerDiscoveryView.qml",
            "HomeAudioAccess.qml",
        ]
        for f in files:
            content = (qml_dir / "pages" / "connections" / f).read_text()
            assert "Accessible" in content, f"{f} missing Accessible properties"

    def test_objectName_on_all_connection_pages(self, qml_dir):
        files = [
            "ConnectionsPage.qml", "ConnectionDetailPage.qml", "MicroServerHero.qml",
            "ConnectionCard.qml", "ConfiguredServerCard.qml", "DiscoveredServerCard.qml",
            "ExternalServerCard.qml", "ManualConnectionDialog.qml",
            "ConnectionCapabilities.qml", "ConnectionErrorPanel.qml",
            "NetworkDiscoveryPanel.qml", "ServerDiscoveryView.qml",
            "HomeAudioAccess.qml",
        ]
        for f in files:
            content = (qml_dir / "pages" / "connections" / f).read_text()
            assert "objectName" in content, f"{f} missing objectName"
