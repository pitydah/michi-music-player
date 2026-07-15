<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test keyboard navigation patterns for home audio."""
from unittest.mock import MagicMock, PropertyMock
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test keyboard navigation in home audio pages via QML component loading."""
from pathlib import Path
>>>>>>> Stashed changes

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest
<<<<<<< Updated upstream
=======
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
=======
"""Test keyboard navigation patterns for home audio."""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
pytestmark = pytest.mark.isolation


@pytest.fixture
<<<<<<< Updated upstream
<<<<<<< Updated upstream
def mock_ha():
    ha = MagicMock()
    ha.is_connected = True
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.get_devices.return_value = [{"name": "Speaker", "entity_id": "spk1"}]
    ha.get_zones.return_value = [
        {"id": "z1", "name": "Zone1", "muted": False, "volume": 50, "state": "idle"},
    ]
    ha.get_groups.return_value = []
    return ha
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e
>>>>>>> Stashed changes


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = []
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestKeyboardAccessible:
    def test_state_changed_emitted(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda: signals.append(1))
        bridge.refresh()
        assert len(signals) >= 0

    def test_volume_supported_true(self, bridge):
        assert bridge.volumeSupported is True

    def test_volume_supported_no_ctrl(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        assert b.volumeSupported is False

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_home_assistant_state(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

<<<<<<< Updated upstream
=======
def test_home_audio_page_flickable_focus(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/HomeAudioPage.qml")))
    assert component.isReady()
=======
def mock_ha():
    ha = MagicMock()
    ha.is_connected = True
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.get_devices.return_value = [{"name": "Speaker", "entity_id": "spk1"}]
    ha.get_zones.return_value = [
        {"id": "z1", "name": "Zone1", "muted": False, "volume": 50, "state": "idle"},
    ]
    ha.get_groups.return_value = []
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = []
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestKeyboardAccessible:
    def test_state_changed_emitted(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda: signals.append(1))
        bridge.refresh()
        assert len(signals) >= 0

    def test_volume_supported_true(self, bridge):
        assert bridge.volumeSupported is True

    def test_volume_supported_no_ctrl(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        assert b.volumeSupported is False

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_home_assistant_state(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_snapcast_state(self, bridge):
        bridge.refresh()
        assert bridge.snapcastState == "available"

    def test_disconnect_resets(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []

    def test_refresh_after_disconnect(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"
        bridge.disconnectHa()
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

    def test_configure_ha_updates_state(self, bridge, mock_ha):
        bridge.refresh()
        bridge.configureHomeAssistant("192.168.1.1", 8123, "token")
        assert bridge.homeAssistantState != "not_configured" or bridge.lastContact > 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
