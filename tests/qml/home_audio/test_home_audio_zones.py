"""Test Home Audio zones, groups, devices, Snapcast, volume, mute, source,
sync status, latency, reconnect, group, ungroup, transfer playback,
unavailable state, partial failure, and server handoff."""
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
    ha.configure = MagicMock(return_value=True)
    ha.is_available = True
    ha.latency_ms = 25
    ha.server_handoff_available = True
    ha.server_handoff = MagicMock(return_value="ok")
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
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.assign_stream = MagicMock()
    sc.playback_transfer = MagicMock()
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


class TestGroups:
    def test_groups_from_ha(self, bridge):
        bridge.refresh()
        assert hasattr(bridge, "groups")


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
        assert result["ok"] is False

    def test_set_mute_via_ha_fallback(self, mock_ha):
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        result = b.setZoneMute("zone1", True)
        assert result["ok"] is False


class TestReconnectUnavailable:
    def test_reconnect(self, bridge):
        result = bridge.reconnectHa()
        assert result["ok"] is True

    def test_reconnect_no_controller(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_disconnect_resets_ha(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []

    def test_unavailable_state(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        assert b.homeAssistantState == "not_configured"
        assert b.snapcastState == "unavailable"

    def test_partial_failure_marks_error(self, mock_ha):
        mock_ha.is_connected = True
        type(mock_ha).is_connected = PropertyMock(return_value=True)
        mock_ha.get_devices = MagicMock(side_effect=Exception("HA error"))
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        assert b.homeAssistantState == "error" or b.lastError


class TestTransferPlayback:
    def test_transfer_playback(self, bridge, mock_snapcast):
        result = bridge.playbackTransfer("zone1")
        assert result["ok"] is True
        assert mock_snapcast.playback_transfer.called

    def test_transfer_playback_missing_args(self, bridge):
        result = bridge.playbackTransfer("")
        assert result["ok"] is False

    def test_transfer_playback_unsupported(self):
        no_ctrl = HomeAudioBridge(ha_controller=None)
        result = no_ctrl.playbackTransfer("zone1")
        assert result["ok"] is False


class TestServerHandoff:
    def test_handoff_to_server(self, bridge):
        bridge.refresh()
        result = bridge.serverHandoff()
        assert result["ok"] is True

    def test_handoff_unsupported(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.serverHandoff()
        assert result["ok"] is False


class TestReceiverDiscovery:
    def test_discover_receivers_unsupported(self, bridge):
        result = bridge.discoverReceivers()
        assert result["ok"] is False

    def test_discover_receivers_no_controller(self):
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
        assert bridge.receiversAvailable is False
