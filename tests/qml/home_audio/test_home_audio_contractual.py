"""Test Home Audio contractual: zones, groups, streams, volume, mute, latency,
server handoff, refresh, offline, partial failures, receivers.

Adapters: SnapcastAdapter, HomeAudioAdapter.
NEVER mark zone available if backend did not confirm it.
"""
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
        {"name": "Living Room Speaker", "entity_id": "media_player.living_room",
         "state": "playing", "room": "Living Room", "type": "speaker"},
        {"name": "Kitchen Speaker", "entity_id": "media_player.kitchen",
         "state": "idle", "room": "Kitchen", "type": "speaker"},
    ]
    ha.get_zones.return_value = [
        {"id": "zone1", "name": "Living Room", "muted": False, "volume": 80,
         "source": "Michi Stream", "latency_ms": 50},
        {"id": "zone2", "name": "Kitchen", "muted": True, "volume": 30,
         "source": "TV", "latency_ms": 100},
    ]
    ha.get_groups.return_value = [
        {"id": "group1", "name": "Whole House", "members": ["zone1", "zone2"],
         "muted": False, "volume": 70},
    ]
    ha.get_source.return_value = {"source": "Michi Stream", "type": "local"}
    ha.get_sync_status.return_value = {"synced": True, "master": "zone1", "latency": 50}
    ha.get_latency = MagicMock(return_value=25)
    ha.configure = MagicMock()
    ha.is_available = True
    ha.reconnect = MagicMock(return_value=True)
    ha.disconnect = MagicMock()
    ha.join = MagicMock()
    ha.unjoin = MagicMock()
    ha.transfer_playback = MagicMock(return_value={"ok": True})
    ha.select_source = MagicMock()
    ha.set_volume = MagicMock()
    ha.set_mute = MagicMock()
    ha.set_latency = MagicMock()
    ha.handoff = MagicMock(return_value={"ok": True})
    ha.discover_receivers = MagicMock(return_value=[
        {"name": "Office Speaker", "host": "192.168.1.200", "type": "snapcast"},
        {"name": "Garage", "host": "192.168.1.201", "type": "snapcast"},
    ])
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "sg1", "name": "Living Room", "muted": False, "volume": 80,
         "stream_id": "default", "latency": 50},
        {"id": "sg2", "name": "Kitchen", "muted": True, "volume": 30,
         "stream_id": "default", "latency": 100},
    ]
    sc.get_clients.return_value = [
        {"name": "snapcast-1", "id": "client1", "connected": True, "host": "192.168.1.10"},
        {"name": "snapcast-2", "id": "client2", "connected": False, "host": "192.168.1.11"},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.assign_stream = MagicMock()
    sc.group = MagicMock()
    sc.ungroup = MagicMock()
    sc.set_latency = MagicMock()
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestZonesContract:
    def test_refresh_populates_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) >= 1

    def test_zone_has_required_fields(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "id" in zone
        assert "name" in zone
        assert "muted" in zone
        assert "volume" in zone

    def test_zone_source_included(self, mock_ha):
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        zone = b.zones[0]
        assert "source" in zone

    def test_zone_latency_included(self, mock_ha):
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        zone = b.zones[0]
        assert "latency_ms" in zone


class TestGroupsContract:
    def test_groups_populated(self, bridge):
        bridge.refresh()
        assert len(bridge.groups) >= 1

    def test_group_has_members(self, bridge):
        bridge.refresh()
        group = bridge.groups[0]
        assert "members" in group
        assert len(group["members"]) >= 1

    def test_group_zones(self, bridge, mock_snapcast):
        result = bridge.groupZones("zone1,zone2")
        assert result["ok"] is True
        assert mock_snapcast.group.called

    def test_group_empty_list(self, bridge):
        result = bridge.groupZones("")
        assert result["ok"] is False
        assert "EMPTY" in result.get("error", "")

    def test_ungroup_zone(self, bridge, mock_snapcast):
        result = bridge.ungroupZone("zone1")
        assert result["ok"] is True
        assert mock_snapcast.ungroup.called


class TestVolumeMuteLatencyContract:
    def test_set_volume(self, bridge, mock_snapcast):
        result = bridge.setZoneVolume("zone1", 0.75)
        assert result["ok"] is True
        assert mock_snapcast.set_group_volume.called

    def test_set_volume_empty_zone(self, bridge):
        result = bridge.setZoneVolume("", 0.5)
        assert result["ok"] is False

    def test_set_mute(self, bridge, mock_snapcast):
        result = bridge.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_snapcast.set_group_mute.called

    def test_set_mute_empty_zone(self, bridge):
        result = bridge.setZoneMute("", True)
        assert result["ok"] is False

    def test_set_latency(self, bridge, mock_snapcast):
        result = bridge.setLatency("zone1", 100)
        assert result["ok"] is True
        assert mock_snapcast.set_latency.called

    def test_set_latency_empty_zone(self, bridge):
        result = bridge.setLatency("", 100)
        assert result["ok"] is False


class TestStreamServerHandoffContract:
    def test_assign_stream(self, bridge, mock_snapcast):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True
        assert mock_snapcast.assign_stream.called

    def test_assign_stream_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.assignStream("stream_main")
        assert result["ok"] is False

    def test_handoff_to_server(self, bridge, mock_ha):
        result = bridge.handoffToServer()
        assert result["ok"] is True
        assert mock_ha.handoff.called

    def test_handoff_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.handoffToServer()
        assert result["ok"] is False

    def test_transfer_playback(self, bridge, mock_ha):
        result = bridge.transferPlayback("zone1", "zone2")
        assert result["ok"] is True
        assert mock_ha.transfer_playback.called

    def test_transfer_playback_missing_args(self, bridge):
        result = bridge.transferPlayback("", "zone2")
        assert result["ok"] is False


class TestOfflinePartialFailureContract:
    def test_offline_backend_not_marked_connected(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        assert b.homeAssistantState == "not_configured"

    def test_partial_failure_marks_error(self, mock_ha):
        mock_ha.is_connected = True
        type(mock_ha).is_connected = PropertyMock(return_value=True)
        mock_ha.get_devices = MagicMock(side_effect=Exception("HA error"))
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        assert b.homeAssistantState in ("error",) or b.lastError

    def test_refresh_no_controller_safe(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.refresh()
        assert result["ok"] is True

    def test_disconnect_resets_all(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []
        assert bridge.zones == []
        assert bridge.latencyMs == 0


class TestReceiverDiscoveryContract:
    def test_discover_receivers(self, bridge, mock_ha):
        result = bridge.discoverReceivers()
        assert result["ok"] is True
        assert mock_ha.discover_receivers.called
        assert result["count"] >= 1
        assert bridge.receiversAvailable is True

    def test_discover_receivers_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.discoverReceivers()
        assert result["ok"] is False
