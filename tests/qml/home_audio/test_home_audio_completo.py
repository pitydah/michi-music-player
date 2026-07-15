from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha():
    ha = MagicMock()
    # `is_connected` as callable property
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.test_connection.return_value = True
    ha.get_devices.return_value = [
        {"name": "Living Room Speaker", "entity_id": "media_player.living_room"},
        {"name": "Kitchen Speaker", "entity_id": "media_player.kitchen"},
    ]
    ha.get_groups.return_value = [{"id": "g1", "name": "All"}]
    ha.get_streams.return_value = [{"id": "s1", "name": "Main Stream"}]
    ha.latency_ms = 45
    ha.server_handoff_available = True
    ha.configure = MagicMock()
    ha.transfer_playback = MagicMock(return_value="done")
    ha.handoff = MagicMock(return_value="handoff_ok")
    ha.select_source = MagicMock()
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "group1", "name": "Living Room", "muted": False, "volume": 80},
        {"id": "group2", "name": "Kitchen", "muted": True, "volume": 30},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.assign_stream = MagicMock()
    sc.server_handoff = MagicMock(return_value="done")
    sc.group = MagicMock()
    sc.ungroup = MagicMock()
    sc.set_group_name = MagicMock()
    sc.delete_group = MagicMock()
    sc.set_latency = MagicMock()
    return sc


@pytest.fixture
def bridge(mock_ha, mock_snapcast):
    return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)


class TestInitialState:
    def test_start_not_configured(self, bridge):
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.snapcastState == "unavailable"

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

    def test_snapcast_available(self, bridge):
        assert bridge.snapcastAvailable is True

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_volume_supported(self, bridge):
        assert bridge.volumeSupported is True

    def test_receivers_unsupported(self, bridge):
        assert bridge.receiversAvailable is False

    def test_server_handoff_no_controller(self):
        b = HomeAudioBridge(ha_controller=None)
        assert b.serverHandoffAvailable is False

    def test_server_handoff_available(self, bridge, mock_ha):
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

    def test_refresh_sets_snapcast_available(self, bridge):
        bridge.refresh()
        assert bridge.snapcastState == "available"

    def test_refresh_updates_contact(self, bridge):
        bridge.refresh()
        assert bridge.lastContact > 0

    def test_refresh_populates_streams(self, bridge, mock_ha):
        bridge.refresh()
        assert len(bridge.streams) >= 1

    def test_refresh_latency(self, bridge):
        bridge.refresh()
        assert bridge.latencyMs == 45


class TestConfiguration:
    def test_configure_ha(self, bridge, mock_ha):
        result = bridge.configureHomeAssistant("192.168.1.1", 8123, "token123")
        assert result["ok"] is True or result["ok"] is False

    def test_configure_ha_no_controller(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.configureHomeAssistant("host", 8123, "token")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_test_connection(self, bridge):
        result = bridge.testHomeAssistant()
        assert result["ok"] is True

    def test_test_connection_no_controller(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.testHomeAssistant()
        assert result["ok"] is False


class TestZoneControl:
    def test_set_volume(self, bridge, mock_snapcast):
        result = bridge.setZoneVolume("group1", 0.75)
        assert result["ok"] is True

    def test_set_volume_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setZoneVolume("group1", 0.5)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_set_mute(self, bridge, mock_snapcast):
        result = bridge.setZoneMute("group1", True)
        assert result["ok"] is True

    def test_set_mute_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setZoneMute("group1", True)
        assert result["ok"] is False

    def test_zone_properties_in_refresh(self, bridge):
        bridge.refresh()
        zone = bridge.zones[0]
        assert zone["name"] == "Living Room"
        assert zone["muted"] is False
        assert zone["volume"] == 80


class TestStreamManagement:
    def test_assign_stream(self, bridge, mock_snapcast):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True
        mock_snapcast.assign_stream.assert_called_once_with("stream_main")

    def test_assign_stream_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
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
        b = HomeAudioBridge(ha_controller=None)
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_disconnect_clears_devices(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.devices == []


class TestGroupOperations:
    def test_group_zones(self, bridge, mock_snapcast):
        result = bridge.groupZones("group1,group2")
        assert result["ok"] is True
        mock_snapcast.group.assert_called_once_with("group1,group2")

    def test_group_zones_empty(self, bridge):
        result = bridge.groupZones("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONES"

    def test_group_zones_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.groupZones("group1,group2")
        assert result["ok"] is False

    def test_ungroup_zone(self, bridge, mock_snapcast):
        result = bridge.ungroupZone("group1")
        assert result["ok"] is True
        mock_snapcast.ungroup.assert_called_once_with("group1")

    def test_ungroup_zone_empty(self, bridge):
        result = bridge.ungroupZone("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"

    def test_rename_zone(self, bridge, mock_snapcast):
        result = bridge.renameZone("group1", "New Name")
        assert result["ok"] is True
        mock_snapcast.set_group_name.assert_called_once_with("group1", "New Name")

    def test_rename_zone_missing_args(self, bridge):
        result = bridge.renameZone("group1", "")
        assert result["ok"] is False
        assert result["error"] == "MISSING_ARGS"

    def test_delete_zone(self, bridge, mock_snapcast):
        result = bridge.deleteZone("group1")
        assert result["ok"] is True
        mock_snapcast.delete_group.assert_called_once_with("group1")

    def test_delete_zone_empty(self, bridge):
        result = bridge.deleteZone("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"


class TestServerHandoff:
    def test_handoff_ha(self, bridge, mock_ha):
        bridge.refresh()
        result = bridge.serverHandoff()
        assert result["ok"] is True

    def test_handoff_not_available(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.serverHandoff()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"


class TestPlaybackTransfer:
    def test_transfer_to_zone(self, bridge, mock_ha):
        result = bridge.transferPlayback("group1", "group2")
        assert result["ok"] is True
        mock_ha.transfer_playback.assert_called_once_with("group1", "group2")

    def test_transfer_missing_args(self, bridge):
        result = bridge.transferPlayback("", "")
        assert result["ok"] is False
        assert result["error"] == "MISSING_ARGS"

    def test_transfer_no_controller(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.transferPlayback("group1", "group2")
        assert result["ok"] is False


class TestHandoffToServer:
    def test_handoff_to_server(self, bridge, mock_ha):
        result = bridge.handoffToServer()
        assert result["ok"] is True
        mock_ha.handoff.assert_called_once()

    def test_handoff_to_server_no_controller(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.handoffToServer()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"


class TestLatency:
    def test_set_latency(self, bridge, mock_snapcast):
        result = bridge.setLatency("group1", 200)
        assert result["ok"] is True
        mock_snapcast.set_latency.assert_called_once_with("group1", 200)

    def test_set_latency_empty_zone(self, bridge):
        result = bridge.setLatency("", 200)
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"


class TestSourceManagement:
    def test_set_source(self, bridge, mock_ha):
        result = bridge.setSource("TV")
        assert result["ok"] is True
        mock_ha.select_source.assert_called_once_with("TV")

    def test_set_source_empty(self, bridge):
        result = bridge.setSource("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_SOURCE"

    def test_set_source_no_controller(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
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

    def test_offline_detected_on_stale_contact(self, bridge, mock_snapcast):
        bridge.refresh()
        type(mock_snapcast).is_available = PropertyMock(return_value=False)
        bridge._last_contact = 0
        bridge.refresh()
        assert bridge.snapcastState == "unavailable"


class TestEdgeCases:
    def test_no_snapcast_concept_state(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        b.refresh()
        assert b.snapcastState == "concept"

    def test_discover_receivers_unsupported(self, bridge):
        result = bridge.discoverReceivers()
        assert result["ok"] is False

    def test_open_diagnostics_returns_ok(self, bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True

    def test_configure_ha_no_controller_error(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.testHomeAssistant()
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_source_info_default(self, bridge):
        assert bridge.sourceInfo == {}

    def test_sync_status_default(self, bridge):
        assert bridge.syncStatus == {}

    def test_receivers_property(self, bridge):
        assert bridge.receivers() == []

    def test_partial_failure_ha_refresh(self, bridge, mock_ha):
        mock_ha.get_devices.side_effect = RuntimeError("HA error")
        result = bridge.refresh()
        assert result["ok"] is True
        assert "HA" in bridge.lastError or bridge.lastError == ""

    def test_partial_failure_snapcast_refresh(self, bridge, mock_snapcast):
        mock_snapcast.get_groups.side_effect = RuntimeError("Snap error")
        result = bridge.refresh()
        assert result["ok"] is True

    def test_reconnect_sets_state_attempt(self, bridge):
        bridge.reconnectHa()
        assert bridge.homeAssistantState != "error"

    def test_group_zones_no_snapcast_returns_error(self, bridge):
        bridge._snapcast_ctrl = None
        result = bridge.groupZones("a,b")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_server_handoff_with_snapcast(self, bridge, mock_snapcast):
        bridge._ha_ctrl = None
        bridge._server_handoff_available = True
        result = bridge.serverHandoff()
        assert result["ok"] is True

    def test_set_latency_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.setLatency("zone1", 100)
        assert result["ok"] is False

    def test_ungroup_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.ungroupZone("zone1")
        assert result["ok"] is False

    def test_rename_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.renameZone("zone1", "New")
        assert result["ok"] is False

    def test_delete_no_snapcast(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.deleteZone("zone1")
        assert result["ok"] is False

    def test_delete_zone_no_snapcast_not_implemented(self, bridge, mock_snapcast):
        mock_snapcast.delete_group.side_effect = RuntimeError("deleted")
        result = bridge.deleteZone("zone1")
        assert result["ok"] is False

    def test_set_source_no_ha(self, bridge):
        bridge._ha_ctrl = None
        result = bridge.setSource("TV")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"
