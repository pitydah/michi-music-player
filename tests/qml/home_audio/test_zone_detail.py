from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha_svc():
    svc = MagicMock()
    type(svc).is_connected = PropertyMock(return_value=True)
    svc.get_zones.return_value = [
        {"id": "z1", "name": "Living Room", "muted": False, "volume": 80},
    ]
    svc.set_volume = MagicMock()
    svc.set_mute = MagicMock()
    svc.set_group_name = MagicMock()
    svc.delete_group = MagicMock()
    svc.set_latency = MagicMock()
    svc.select_source = MagicMock()
    return svc


@pytest.fixture
def bridge(mock_ha_svc):
    return HomeAudioBridge(home_audio_service=mock_ha_svc)


class TestZoneDetail:
    def test_zone_select(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert zone["id"] == "z1"
        assert zone["name"] == "Living Room"

    def test_zone_volume(self, bridge, mock_ha_svc):
        result = bridge.setZoneVolume("z1", 0.5)
        assert result["ok"]

    def test_zone_mute(self, bridge, mock_ha_svc):
        result = bridge.setZoneMute("z1", True)
        assert result["ok"]

    def test_zone_rename(self, bridge, mock_ha_svc):
        result = bridge.renameZone("z1", "New Name")
        assert result["ok"]
        mock_ha_svc.set_group_name.assert_called_once_with("z1", "New Name")

    def test_zone_delete(self, bridge, mock_ha_svc):
        result = bridge.deleteZone("z1")
        assert result["ok"]
        mock_ha_svc.delete_group.assert_called_once_with("z1")

    def test_zone_latency_set(self, bridge, mock_ha_svc):
        result = bridge.setLatency("z1", 100)
        assert result["ok"]
        mock_ha_svc.set_latency.assert_called_once_with("z1", 100)

    def test_zone_source_change(self, bridge, mock_ha_svc):
        result = bridge.setSource("HDMI")
        assert result["ok"]
        mock_ha_svc.select_source.assert_called_once_with("HDMI")

    def test_zone_detail_accessible(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "id" in zone
        assert "name" in zone
        assert "muted" in zone
        assert "volume" in zone
