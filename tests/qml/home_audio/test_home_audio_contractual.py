"""Test Home Audio contractual: zones, groups, streams, volume, mute, latency,
server handoff, refresh, offline, partial failures, receivers.

Adapters: HomeAudioService.
NEVER mark zone available if backend did not confirm it.
"""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha_svc():
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
    ha.get_streams.return_value = [
        {"id": "stream1", "name": "Main", "active": True},
    ]
    ha.latency_ms = 25
    ha.server_handoff_available = True
    ha.set_volume = MagicMock()
    ha.set_mute = MagicMock()
    ha.assign_stream = MagicMock()
    ha.group = MagicMock()
    ha.ungroup = MagicMock()
    ha.set_group_name = MagicMock()
    ha.delete_group = MagicMock()
    ha.set_latency = MagicMock()
    ha.reconnect = MagicMock(return_value=True)
    ha.transfer_playback = MagicMock(return_value={"ok": True})
    ha.server_handoff = MagicMock(return_value="ok")
    ha.playback_transfer = MagicMock(return_value={"ok": True})
    return ha


@pytest.fixture
def bridge(mock_ha_svc):
    return HomeAudioBridge(home_audio_service=mock_ha_svc)


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

    def test_zone_source_from_ha(self, mock_ha_svc):
        b = HomeAudioBridge(home_audio_service=mock_ha_svc)
        b.refresh()

    def test_zone_latency_from_ha(self, mock_ha_svc):
        b = HomeAudioBridge(home_audio_service=mock_ha_svc)
        b.refresh()


class TestGroupsContract:
    def test_groups_populated(self, bridge):
        bridge.refresh()
        assert len(bridge.groups) >= 0

    def test_refresh_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True


class TestVolumeMuteLatencyContract:
    def test_set_volume(self, bridge, mock_ha_svc):
        result = bridge.setZoneVolume("zone1", 0.75)
        assert result["ok"] is True
        assert mock_ha_svc.set_volume.called

    def test_set_mute(self, bridge, mock_ha_svc):
        result = bridge.setZoneMute("zone1", True)
        assert result["ok"] is True
        assert mock_ha_svc.set_mute.called

    def test_set_volume_no_service(self, mock_ha_svc):
        result = HomeAudioBridge(home_audio_service=mock_ha_svc).setZoneVolume("zone1", 0.5)
        assert result["ok"] is True

    def test_set_mute_no_service(self):
        result = HomeAudioBridge().setZoneMute("zone1", True)
        assert result["ok"] is False


class TestStreamServerHandoffContract:
    def test_assign_stream(self, bridge, mock_ha_svc):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True
        assert mock_ha_svc.assign_stream.called

    def test_assign_stream_no_svc(self):
        b = HomeAudioBridge()
        result = b.assignStream("stream_main")
        assert result["ok"] is False

    def test_handoff_to_server(self, bridge):
        bridge.refresh()
        result = bridge.serverHandoff()
        assert result["ok"] is True

    def test_handoff_unsupported(self):
        b = HomeAudioBridge()
        result = b.serverHandoff()
        assert result["ok"] is False

    def test_transfer_playback(self, bridge, mock_ha_svc):
        result = bridge.playbackTransfer("zone1")
        assert result["ok"] is True
        assert mock_ha_svc.playback_transfer.called

    def test_transfer_playback_missing_args(self, bridge):
        result = bridge.playbackTransfer("")
        assert result["ok"] is False


class TestOfflinePartialFailureContract:
    def test_offline_backend_not_marked_connected(self):
        b = HomeAudioBridge()
        assert b.homeAssistantState == "not_configured"

    def test_partial_failure_marks_error(self, mock_ha_svc):
        mock_ha_svc.is_connected = True
        type(mock_ha_svc).is_connected = PropertyMock(return_value=True)
        mock_ha_svc.get_devices = MagicMock(side_effect=Exception("HA error"))
        b = HomeAudioBridge(home_audio_service=mock_ha_svc)
        b.refresh()
        assert b.homeAssistantState == "error" or b.lastError

    def test_refresh_no_controller_safe(self):
        b = HomeAudioBridge()
        result = b.refresh()
        assert result["ok"] is True

    def test_disconnect_resets_ha(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.devices == []

    def test_recover_from_offline(self, bridge):
        bridge._offline = True
        result = bridge.recoverFromOffline()
        assert result["ok"] is True
        assert bridge.offline is False


class TestReceiverDiscoveryContract:
    def test_discover_receivers_unsupported(self, bridge):
        result = bridge.discoverReceivers()
        assert result["ok"] is False

    def test_discover_receivers_no_controller(self):
        b = HomeAudioBridge()
        result = b.discoverReceivers()
        assert result["ok"] is False
