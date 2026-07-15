"""Test zone detail page with mock bridge."""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha():
    ha = MagicMock()
    ha.is_connected = True
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.test_connection.return_value = True
    ha.get_devices.return_value = [
        {"name": "Speaker1", "entity_id": "spk1", "state": "playing"},
    ]
    ha.set_volume = MagicMock()
    ha.set_mute = MagicMock()
    ha.reconnect = MagicMock()
    ha.select_source = MagicMock()
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "zone1", "name": "Living Room", "muted": False, "volume": 80,
         "stream_id": "default", "latency": 50},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.group = MagicMock()
    sc.ungroup = MagicMock()
    sc.set_group_name = MagicMock()
    sc.delete_group = MagicMock()
    sc.set_latency = MagicMock()
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestZoneDetail:
    def test_refresh_populates_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) >= 1

    def test_zone_has_all_properties(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "id" in zone
        assert "name" in zone

    def test_zone_volume_change(self, bridge, mock_snapcast):
        result = bridge.setZoneVolume("zone1", 0.75)
        assert result["ok"] is True
        assert mock_snapcast.set_group_volume.called

    def test_zone_mute_toggle(self, bridge, mock_snapcast):
        result = bridge.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_snapcast.set_group_mute.called

    def test_zone_reconnect(self, bridge, mock_ha):
        result = bridge.reconnectHa()
        assert result["ok"] is True
        assert mock_ha.test_connection.called

    def test_zone_group(self, bridge, mock_snapcast):
        result = bridge.groupZones("zone1,zone2")
        assert result["ok"] is True
        assert mock_snapcast.group.called

    def test_zone_ungroup(self, bridge, mock_snapcast):
        result = bridge.ungroupZone("zone1")
        assert result["ok"] is True
        assert mock_snapcast.ungroup.called

    def test_zone_rename(self, bridge, mock_snapcast):
        result = bridge.renameZone("zone1", "New Name")
        assert result["ok"] is True
        assert mock_snapcast.set_group_name.called

    def test_zone_delete(self, bridge, mock_snapcast):
        result = bridge.deleteZone("zone1")
        assert result["ok"] is True
        assert mock_snapcast.delete_group.called

    def test_zone_latency_set(self, bridge, mock_snapcast):
        result = bridge.setLatency("zone1", 100)
        assert result["ok"] is True
        assert mock_snapcast.set_latency.called

    def test_zone_source_change(self, bridge, mock_ha):
        result = bridge.setSource("TV")
        assert result["ok"] is True
        assert mock_ha.select_source.called


class TestZoneDetailNoController:
    def test_set_volume_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setZoneVolume("zone1", 0.5)
        assert result["ok"] is False

    def test_set_mute_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setZoneMute("zone1", True)
        assert result["ok"] is False

    def test_group_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.groupZones("zone1,zone2")
        assert result["ok"] is False

    def test_ungroup_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.ungroupZone("zone1")
        assert result["ok"] is False

    def test_rename_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.renameZone("zone1", "New")
        assert result["ok"] is False

    def test_delete_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.deleteZone("zone1")
        assert result["ok"] is False

    def test_latency_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setLatency("zone1", 100)
        assert result["ok"] is False

    def test_source_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.setSource("TV")
        assert result["ok"] is False
