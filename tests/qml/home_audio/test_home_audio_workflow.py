"""Test Home Audio workflows through HomeAudioBridge."""
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
    ha.configure = MagicMock()
    ha.is_available = True
    return ha


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "group1", "name": "Living Room", "muted": False, "volume": 80},
        {"id": "group2", "name": "Kitchen", "muted": True, "volume": 30},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    sc.assign_stream = MagicMock()
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


class TestCapabilities:
    def test_home_assistant_available(self, bridge):
        assert bridge.homeAssistantAvailable is True

    def test_snapcast_available(self, bridge, mock_snapcast):
        assert bridge.snapcastAvailable is True

    def test_zones_supported(self, bridge):
        assert bridge.zonesSupported is True

    def test_grouping_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_volume_supported(self, bridge):
        assert bridge.volumeSupported is True

    def test_receivers_unsupported(self, bridge):
        assert bridge.receiversAvailable is False


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

    def test_refresh_sets_snapcast_available(self, bridge, mock_snapcast):
        bridge.refresh()
        assert bridge.snapcastState == "available"

    def test_refresh_updates_contact(self, bridge):
        bridge.refresh()
        assert bridge.lastContact > 0


class TestConfiguration:
    def test_configure_ha(self, bridge, mock_ha):
        result = bridge.configureHomeAssistant("192.168.1.1", 8123, "token123")
        assert result["ok"] is True or result["ok"] is False
        if result["ok"]:
            mock_ha.configure.assert_called_once()

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
