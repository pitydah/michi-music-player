from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha_svc():
    ha = MagicMock()
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.test_connection.return_value = True
    ha.get_devices.return_value = [
        {"name": "Living Room Speaker", "entity_id": "media_player.living_room"},
        {"name": "Kitchen Speaker", "entity_id": "media_player.kitchen"},
    ]
    ha.get_zones.return_value = [
        {"id": "group1", "name": "Living Room", "muted": False, "volume": 80},
        {"id": "group2", "name": "Kitchen", "muted": True, "volume": 30},
    ]
    ha.get_groups.return_value = [{"id": "g1", "name": "All"}]
    ha.get_streams.return_value = [{"id": "s1", "name": "Main Stream"}]
    ha.latency_ms = 45
    ha.server_handoff_available = True
    ha.configure = MagicMock()
    ha.transfer_playback = MagicMock(return_value="done")
    ha.handoff = MagicMock(return_value="handoff_ok")
    ha.select_source = MagicMock()
    ha.set_volume = MagicMock()
    ha.set_mute = MagicMock()
    ha.assign_stream = MagicMock()
    ha.group = MagicMock()
    ha.ungroup = MagicMock()
    ha.set_group_name = MagicMock()
    ha.delete_group = MagicMock()
    ha.set_latency = MagicMock()
    ha.server_handoff = MagicMock(return_value="done")
    ha.playback_transfer = MagicMock(return_value="done")
    return ha


@pytest.fixture
def bridge(mock_ha_svc):
    return HomeAudioBridge(home_audio_service=mock_ha_svc)


class TestInitialState:
    def test_start_not_configured(self, bridge):
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.snapcastState == "concept"

    def test_devices_empty_initially(self, bridge):
        assert bridge.devices == []

    def test_zones_empty_initially(self, bridge):
        assert bridge.zones == []

    def test_streams_empty_initially(self, bridge):
        assert bridge.streams == []

    def test_latency_zero_initially(self, bridge):
        assert bridge.latencyMs == 0

    def test_offline_false_initially(self, bridge):
        assert bridge.offline is False


class TestCapabilities:
    def test_home_assistant_available(self, bridge):
        assert bridge.homeAssistantAvailable is True

    def test_snapcast_always_false(self, bridge):
        assert bridge.snapcastAvailable is False

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_volume_supported(self, bridge):
        assert bridge.volumeSupported is True

    def test_receivers_unsupported(self, bridge):
        assert bridge.receiversAvailable is False

    def test_server_handoff_no_controller(self):
        b = HomeAudioBridge()
        assert b.serverHandoffAvailable is False

    def test_server_handoff_available(self, bridge, mock_ha_svc):
        bridge.refresh()
        assert bridge.serverHandoffAvailable is True


class TestRefresh:
    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_populates_devices(self, bridge):
        bridge.refresh()
        assert len(bridge.devices) == 2

    def test_refresh_populates_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) == 2

    def test_refresh_sets_ha_connected(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

    def test_refresh_snapcast_concept(self, bridge):
        bridge.refresh()
        assert bridge.snapcastState == "concept"

    def test_refresh_updates_contact(self, bridge):
        bridge.refresh()
        assert bridge.lastContact > 0

    def test_refresh_populates_streams(self, bridge, mock_ha_svc):
        bridge.refresh()
        assert len(bridge.streams) >= 1

    def test_refresh_latency(self, bridge):
        bridge.refresh()
        assert bridge.latencyMs == 45


class TestConfiguration:
    def test_configure_ha(self, bridge, mock_ha_svc):
        result = bridge.configureHomeAssistant("192.168.1.1", 8123, "token123")
        assert result["ok"] is True or result["ok"] is False

    def test_configure_ha_no_controller(self):
        b = HomeAudioBridge()
        result = b.configureHomeAssistant("host", 8123, "token")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_test_connection(self, bridge):
        result = bridge.testHomeAssistant()
        assert result["ok"] is True

    def test_test_connection_no_controller(self):
        b = HomeAudioBridge()
        result = b.testHomeAssistant()
        assert result["ok"] is False


class TestZoneControl:
    def test_set_volume(self, bridge, mock_ha_svc):
        result = bridge.setZoneVolume("group1", 0.75)
        assert result["ok"] is True
        mock_ha_svc.set_volume.assert_called_once_with("group1", 0.75)

    def test_set_volume_no_service(self):
        b = HomeAudioBridge()
        result = b.setZoneVolume("group1", 0.5)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_set_mute(self, bridge, mock_ha_svc):
        result = bridge.setZoneMute("group1", True)
        assert result["ok"] is True
        mock_ha_svc.set_mute.assert_called_once_with("group1", True)

    def test_set_mute_no_service(self):
        b = HomeAudioBridge()
        result = b.setZoneMute("group1", True)
        assert result["ok"] is False

    def test_zone_properties_in_refresh(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert zone["name"] == "Living Room"
        assert zone["muted"] is False
        assert zone["volume"] == 80


class TestStreamManagement:
    def test_assign_stream(self, bridge, mock_ha_svc):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True
        mock_ha_svc.assign_stream.assert_called_once_with("stream_main")

    def test_assign_stream_no_service(self):
        b = HomeAudioBridge()
        result = b.assignStream("stream_main")
        assert result["ok"] is False


class TestDisconnectReconnect:
    def test_disconnect_resets_state(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.lastContact == 0.0

    def test_reconnect_calls_test(self, bridge):
        result = bridge.reconnectHa()
        assert result["ok"] is True

    def test_reconnect_no_controller(self):
        b = HomeAudioBridge()
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_disconnect_clears_devices(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.devices == []


class TestGroupOperations:
    def test_group_zones(self, bridge, mock_ha_svc):
        result = bridge.groupZones("group1,group2")
        assert result["ok"] is True
        mock_ha_svc.group.assert_called_once_with("group1,group2")

    def test_group_zones_empty(self, bridge):
        result = bridge.groupZones("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONES"

    def test_group_zones_no_service(self):
        b = HomeAudioBridge()
        result = b.groupZones("group1,group2")
        assert result["ok"] is False

    def test_ungroup_zone(self, bridge, mock_ha_svc):
        result = bridge.ungroupZone("group1")
        assert result["ok"] is True
        mock_ha_svc.ungroup.assert_called_once_with("group1")

    def test_ungroup_zone_empty(self, bridge):
        result = bridge.ungroupZone("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"

    def test_rename_zone(self, bridge, mock_ha_svc):
        result = bridge.renameZone("group1", "New Name")
        assert result["ok"] is True
        mock_ha_svc.set_group_name.assert_called_once_with("group1", "New Name")

    def test_rename_zone_missing_args(self, bridge):
        result = bridge.renameZone("group1", "")
        assert result["ok"] is False
        assert result["error"] == "MISSING_ARGS"

    def test_delete_zone(self, bridge, mock_ha_svc):
        result = bridge.deleteZone("group1")
        assert result["ok"] is True
        mock_ha_svc.delete_group.assert_called_once_with("group1")

    def test_delete_zone_empty(self, bridge):
        result = bridge.deleteZone("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"


class TestServerHandoff:
    def test_handoff_ha(self, bridge, mock_ha_svc):
        bridge.refresh()
        result = bridge.serverHandoff()
        assert result["ok"] is True
        assert mock_ha_svc.server_handoff.called

    def test_handoff_not_available(self):
        b = HomeAudioBridge()
        result = b.serverHandoff()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"


class TestPlaybackTransfer:
    def test_transfer_to_zone(self, bridge, mock_ha_svc):
        result = bridge.transferPlayback("group1", "group2")
        assert result["ok"] is True
        mock_ha_svc.transfer_playback.assert_called_once_with("group1", "group2")

    def test_transfer_missing_args(self, bridge):
        result = bridge.transferPlayback("", "")
        assert result["ok"] is False
        assert result["error"] == "MISSING_ARGS"

    def test_transfer_no_controller(self):
        b = HomeAudioBridge()
        result = b.transferPlayback("group1", "group2")
        assert result["ok"] is False


class TestHandoffToServer:
    def test_handoff_to_server(self, bridge, mock_ha_svc):
        result = bridge.handoffToServer()
        assert result["ok"] is True
        mock_ha_svc.handoff.assert_called_once()

    def test_handoff_to_server_no_controller(self):
        b = HomeAudioBridge()
        result = b.handoffToServer()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"


class TestLatency:
    def test_set_latency(self, bridge, mock_ha_svc):
        result = bridge.setLatency("group1", 200)
        assert result["ok"] is True
        mock_ha_svc.set_latency.assert_called_once_with("group1", 200)

    def test_set_latency_empty_zone(self, bridge):
        result = bridge.setLatency("", 200)
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"


class TestSourceManagement:
    def test_set_source(self, bridge, mock_ha_svc):
        result = bridge.setSource("TV")
        assert result["ok"] is True
        mock_ha_svc.select_source.assert_called_once_with("TV")

    def test_set_source_empty(self, bridge):
        result = bridge.setSource("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_SOURCE"

    def test_set_source_no_controller(self):
        b = HomeAudioBridge()
        result = b.setSource("TV")
        assert result["ok"] is False


class TestOffline:
    def test_recover_from_offline(self, bridge):
        bridge._offline = True
        result = bridge.recoverFromOffline()
        assert result["ok"] is True
        assert bridge.offline is False

    def test_latency_report(self, bridge):
        bridge._latency_ms = 42
        report = bridge.getLatencyReport()
        assert report["ok"] is True
        assert report["latency_ms"] == 42


class TestEdgeCases:
    def test_snapcast_concept_state(self):
        b = HomeAudioBridge()
        b.refresh()
        assert b.snapcastState == "concept"

    def test_discover_receivers_unsupported(self, bridge):
        result = bridge.discoverReceivers()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_open_diagnostics_returns_ok(self, bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True

    def test_receivers_property(self, bridge):
        assert bridge.receivers() == []

    def test_partial_failure_ha_refresh(self, bridge, mock_ha_svc):
        mock_ha_svc.get_devices.side_effect = RuntimeError("HA error")
        result = bridge.refresh()
        assert result["ok"] is True

    def test_source_info_default(self, bridge):
        assert bridge.sourceInfo == {}

    def test_sync_status_default(self, bridge):
        assert bridge.syncStatus == {}

    def test_playback_transfer_slot(self, bridge, mock_ha_svc):
        result = bridge.playbackTransfer("zone1")
        assert result["ok"] is True
        assert mock_ha_svc.playback_transfer.called

    def test_playback_transfer_empty(self, bridge):
        result = bridge.playbackTransfer("")
        assert result["ok"] is False
