"""CP — Home Audio: zones, groups, streams, volume, mute, latency, server handoff, refresh, offline, partial failure."""
from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge

pytestmark = pytest.mark.isolation


class TestHomeAudioEnhanced:
    @pytest.fixture
    def mock_ha_svc(self):
        ha = MagicMock()
        ha.is_connected = True
        type(ha).is_connected = PropertyMock(return_value=True)
        ha.test_connection.return_value = True
        ha.get_devices.return_value = [
            {"name": "Living Room", "entity_id": "media_player.living_room"},
            {"name": "Kitchen", "entity_id": "media_player.kitchen"},
        ]
        ha.get_zones.return_value = [
            {"id": "g1", "name": "Living Room", "muted": False, "volume": 80},
            {"id": "g2", "name": "Kitchen", "muted": True, "volume": 30},
        ]
        ha.set_volume = MagicMock()
        ha.set_mute = MagicMock()
        ha.assign_stream = MagicMock()
        return ha

    @pytest.fixture
    def bridge(self, mock_ha_svc):
        return HomeAudioBridge(home_audio_service=mock_ha_svc)

    def test_initial_state(self, bridge):
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.snapcastState == "concept"

    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_populates_devices(self, bridge):
        bridge.refresh()
        assert len(bridge.devices) >= 1

    def test_refresh_populates_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) >= 1

    def test_refresh_sets_ha_connected(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "connected"

    def test_refresh_updates_contact(self, bridge):
        bridge.refresh()
        assert bridge.lastContact > 0

    def test_configure_ha_no_controller(self):
        b = HomeAudioBridge()
        result = b.configureHomeAssistant("host", 8123, "token")
        assert result["ok"] is False

    def test_test_connection(self, bridge):
        result = bridge.testHomeAssistant()
        assert result["ok"] is True

    def test_test_connection_no_controller(self):
        b = HomeAudioBridge()
        result = b.testHomeAssistant()
        assert result["ok"] is False

    def test_set_zone_volume(self, bridge, mock_ha_svc):
        result = bridge.setZoneVolume("g1", 0.75)
        assert result["ok"] is True
        mock_ha_svc.set_volume.assert_called_once_with("g1", 0.75)

    def test_set_zone_volume_no_service(self):
        b = HomeAudioBridge()
        result = b.setZoneVolume("g1", 0.5)
        assert result["ok"] is False

    def test_set_zone_mute(self, bridge, mock_ha_svc):
        result = bridge.setZoneMute("g1", True)
        assert result["ok"] is True
        mock_ha_svc.set_mute.assert_called_once_with("g1", True)

    def test_set_zone_mute_no_service(self):
        b = HomeAudioBridge()
        result = b.setZoneMute("g1", True)
        assert result["ok"] is False

    def test_assign_stream(self, bridge, mock_ha_svc):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True
        mock_ha_svc.assign_stream.assert_called_once_with("stream_main")

    def test_assign_stream_no_service(self):
        b = HomeAudioBridge()
        result = b.assignStream("stream_main")
        assert result["ok"] is False

    def test_disconnect(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"

    def test_reconnect(self, bridge):
        result = bridge.reconnectHa()
        assert result["ok"] is True

    def test_reconnect_no_controller(self):
        b = HomeAudioBridge()
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_snapcast_concept(self):
        b = HomeAudioBridge()
        b.refresh()
        assert b.snapcastState == "concept"

    def test_capabilities(self, bridge):
        assert bridge.homeAssistantAvailable is True
        assert bridge.snapcastAvailable is False
        assert bridge.zonesSupported is True
        assert bridge.volumeSupported is True

    def test_open_diagnostics(self, bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True
