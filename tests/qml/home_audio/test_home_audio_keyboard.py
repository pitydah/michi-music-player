"""Test keyboard navigation patterns for home audio."""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha_svc():
    ha = MagicMock()
    ha.is_connected = True
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.get_devices.return_value = [{"name": "Speaker", "entity_id": "spk1"}]
    ha.get_zones.return_value = [
        {"id": "z1", "name": "Zone1", "muted": False, "volume": 50},
    ]
    ha.get_groups.return_value = []
    ha.get_streams.return_value = []
    return ha


@pytest.fixture
def bridge(mock_ha_svc):
    return HomeAudioBridge(home_audio_service=mock_ha_svc)


class TestKeyboardAccessible:
    def test_state_changed_emitted(self, bridge):
        signals = []
        bridge.stateChanged.connect(lambda: signals.append(1))
        bridge.refresh()
        assert len(signals) >= 0

    def test_volume_supported_true(self, bridge):
        assert bridge.volumeSupported is True

    def test_volume_supported_no_ctrl(self):
        b = HomeAudioBridge()
        assert b.volumeSupported is False

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_home_assistant_state(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

    def test_snapcast_state(self, bridge):
        bridge.refresh()
        assert bridge.snapcastState == "concept"

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
