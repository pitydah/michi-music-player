"""Full workflow: select zones -> group -> change volume -> ungroup."""
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
        {"name": "Living Room Speaker", "entity_id": "media_player.living_room"},
        {"name": "Kitchen Speaker", "entity_id": "media_player.kitchen"},
    ]
    ha.set_volume = MagicMock()
    ha.set_mute = MagicMock()
    ha.reconnect = MagicMock()
    ha.select_source = MagicMock()
    ha.join = MagicMock()
    ha.unjoin = MagicMock()
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "zone1", "name": "Living Room", "muted": False, "volume": 80, "stream_id": "s1"},
        {"id": "zone2", "name": "Kitchen", "muted": True, "volume": 30, "stream_id": "s1"},
        {"id": "zone3", "name": "Bedroom", "muted": False, "volume": 50, "stream_id": "s2"},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.group = MagicMock()
    sc.ungroup = MagicMock()
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestFullWorkflow:
    def test_select_zones_and_group(self, bridge, mock_snapcast):
        bridge.refresh()
        assert len(bridge.zones) >= 3
        result = bridge.groupZones("zone1,zone2")
        assert result["ok"] is True
        assert mock_snapcast.group.called

    def test_group_then_change_volume(self, bridge, mock_snapcast):
        bridge.groupZones("zone1,zone2")
        result = bridge.setZoneVolume("zone1", 0.9)
        assert result["ok"] is True
        assert mock_snapcast.set_group_volume.called

    def test_group_then_mute(self, bridge, mock_snapcast):
        bridge.groupZones("zone1,zone2")
        result = bridge.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_snapcast.set_group_mute.called

    def test_group_then_ungroup(self, bridge, mock_snapcast):
        bridge.groupZones("zone1,zone2")
        result = bridge.ungroupZone("zone1")
        assert result["ok"] is True
        assert mock_snapcast.ungroup.called

    def test_volume_multiple_zones(self, bridge, mock_snapcast):
        for zone in ["zone1", "zone2", "zone3"]:
            result = bridge.setZoneVolume(zone, 0.5)
            assert result["ok"] is True
        assert mock_snapcast.set_group_volume.call_count >= 3

    def test_group_all_three(self, bridge, mock_snapcast):
        result = bridge.groupZones("zone1,zone2,zone3")
        assert result["ok"] is True
        assert mock_snapcast.group.called

    def test_ungroup_all(self, bridge, mock_snapcast):
        for zone in ["zone1", "zone2", "zone3"]:
            result = bridge.ungroupZone(zone)
            assert result["ok"] is True
        assert mock_snapcast.ungroup.call_count >= 3

    def test_refresh_after_group(self, bridge):
        bridge.groupZones("zone1,zone2")
        bridge.refresh()
        assert len(bridge.zones) >= 3

    def test_disconnect_after_workflow(self, bridge):
        bridge.refresh()
        bridge.groupZones("zone1,zone2")
        bridge.setZoneVolume("zone1", 0.5)
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []

    def test_full_lifecycle(self, bridge, mock_snapcast, mock_ha):
        bridge.refresh()
        assert len(bridge.zones) >= 3
        assert len(bridge.devices) >= 2

        bridge.groupZones("zone1,zone2")
        assert mock_snapcast.group.called

        bridge.setZoneVolume("group1", 0.75)
        assert mock_snapcast.set_group_volume.called or mock_ha.set_volume.called

        bridge.setZoneMute("group1", False)
        assert mock_snapcast.set_group_mute.called or mock_ha.set_mute.called

        bridge.reconnectHa()
        assert mock_ha.test_connection.called

        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"

    def test_config_lifecycle(self, bridge, mock_ha):
        bridge.configureHomeAssistant("192.168.1.1", 8123, "token")
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.lastContact == 0.0

    def test_stream_lifecycle(self, bridge, mock_snapcast):
        bridge.assignStream("stream_main")
        assert mock_snapcast.assign_stream.called
        bridge.refresh()
        assert bridge.snapcastState == "available"

    def test_diagnostics_lifecycle(self, bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True

    def test_no_controller_full_workflow(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        b.refresh()
        assert b.snapcastState == "concept"
        assert b.devices == []
        result = b.setZoneVolume("z1", 0.5)
        assert result["ok"] is False
        result = b.groupZones("z1,z2")
        assert result["ok"] is False
        b.disconnectHa()
        assert b.homeAssistantState == "not_configured"
