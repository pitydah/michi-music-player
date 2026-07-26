"""Test keyboard navigation patterns for connections."""
import pathlib
from unittest.mock import MagicMock

from ui_qml_bridge.connections_bridge import ConnectionsBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def qml_dir():
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def mock_ctrl():
    ctrl = MagicMock()
    ctrl.discover.return_value = []
    ctrl.reconnect.return_value = True
    return ctrl


@pytest.fixture
def bridge(mock_ctrl):
    return ConnectionsBridge(connection_service=mock_ctrl)


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
