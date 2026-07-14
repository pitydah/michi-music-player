"""Test Home Audio zones, groups, devices, Snapcast, volume, mute, source,
sync status, latency, reconnect, group, ungroup, transfer playback,
unavailable state, partial failure, and server handoff."""
from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


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
    ha.configure = MagicMock(return_value=True)
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
    ]
    sc.get_clients.return_value = [
        {"name": "snapcast-1", "id": "client1", "connected": True, "host": "192.168.1.10"},
        {"name": "snapcast-2", "id": "client2", "connected": False, "host": "192.168.1.11"},
    ]
    sc.get_groups.return_value = [
        {"id": "sg1", "name": "Living Room", "muted": False, "volume": 80,
         "stream_id": "default", "latency": 50},
        {"id": "sg2", "name": "Kitchen", "muted": True, "volume": 30,
         "stream_id": "default", "latency": 100},
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


class TestZones:
    def test_refresh_populates_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) >= 2

    def test_zone_has_properties(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "id" in zone
        assert "name" in zone
        assert "muted" in zone
        assert "volume" in zone

    def test_zone_source_included(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "source" in zone

    def test_zone_latency_included(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert "latency_ms" in zone


class TestGroups:
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

    def test_ungroup_zone(self, bridge, mock_snapcast):
        result = bridge.ungroupZone("zone1")
        assert result["ok"] is True
        assert mock_snapcast.ungroup.called

    def test_ungroup_empty(self, bridge):
        result = bridge.ungroupZone("")
        assert result["ok"] is False


class TestVolumeMute:
    def test_set_zone_volume(self, bridge, mock_snapcast):
        result = bridge.setZoneVolume("zone1", 0.75)
        assert result["ok"] is True
        assert mock_snapcast.set_group_volume.called

    def test_set_mute(self, bridge, mock_snapcast):
        result = bridge.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_snapcast.set_group_mute.called

    def test_set_volume_via_ha_fallback(self, mock_ha):
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        result = b.setZoneVolume("zone1", 0.5)
        assert result["ok"] is True
        assert mock_ha.set_volume.called

    def test_set_mute_via_ha_fallback(self, mock_ha):
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        result = b.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_ha.set_mute.called


class TestSourceSync:
    def test_source_info_populated(self, bridge):
        bridge.refresh()
        assert bridge.sourceInfo
        info = bridge.sourceInfo[0]
        assert "source" in info

    def test_set_source(self, bridge, mock_ha):
        result = bridge.setSource("TV")
        assert result["ok"] is True
        assert mock_ha.select_source.called

    def test_set_source_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.setSource("TV")
        assert result["ok"] is False

    def test_sync_status_populated(self, bridge):
        bridge.refresh()
        assert bridge.syncStatus
        status = bridge.syncStatus[0]
        assert "synced" in status or "latency" in status


class TestLatency:
    def test_latency_measured(self, bridge, mock_ha):
        bridge.refresh()
        assert bridge.latencyMs == 25

    def test_set_latency(self, bridge, mock_snapcast):
        result = bridge.setLatency("zone1", 100)
        assert result["ok"] is True
        assert mock_snapcast.set_latency.called

    def test_set_latency_unsupported(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setLatency("zone1", 100)
        assert result["ok"] is False


class TestReconnectUnavailable:
    def test_reconnect(self, bridge, mock_ha):
        result = bridge.reconnectHa()
        assert result["ok"] is True
        assert mock_ha.reconnect.called

    def test_reconnect_no_controller(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_disconnect_resets_all(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []
        assert bridge.zones == []
        assert bridge.latencyMs == 0

    def test_unavailable_state(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        assert b.homeAssistantState == "not_configured"
        assert b.snapcastState == "unavailable"

    def test_partial_failure_marks_partial(self, mock_ha):
        mock_ha.is_connected = True
        type(mock_ha).is_connected = PropertyMock(return_value=True)
        mock_ha.get_devices = MagicMock(side_effect=Exception("HA error"))
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        assert b.homeAssistantState in ("error", "partial") or b.lastError


class TestTransferPlayback:
    def test_transfer_playback(self, bridge, mock_ha):
        result = bridge.transferPlayback("zone1", "zone2")
        assert result["ok"] is True
        assert mock_ha.transfer_playback.called

    def test_transfer_playback_missing_args(self, bridge):
        result = bridge.transferPlayback("", "zone2")
        assert result["ok"] is False

    def test_transfer_playback_unsupported(self):
        no_ctrl = HomeAudioBridge(ha_controller=None)
        result = no_ctrl.transferPlayback("zone1", "zone2")
        assert result["ok"] is False


class TestServerHandoff:
    def test_handoff_to_server(self, bridge, mock_ha):
        result = bridge.handoffToServer()
        assert result["ok"] is True
        assert mock_ha.handoff.called

    def test_handoff_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.handoffToServer()
        assert result["ok"] is False


class TestReceiverDiscovery:
    def test_discover_receivers(self, bridge, mock_ha):
        result = bridge.discoverReceivers()
        assert result["ok"] is True
        assert mock_ha.discover_receivers.called
        assert result["count"] >= 1

    def test_discover_receivers_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.discoverReceivers()
        assert result["ok"] is False


class TestCapabilities:
    def test_home_assistant_available(self, bridge):
        assert bridge.homeAssistantAvailable is True

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_receivers_available(self, bridge):
        assert bridge.receiversAvailable is True
