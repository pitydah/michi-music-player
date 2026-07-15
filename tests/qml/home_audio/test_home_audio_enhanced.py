from __future__ import annotations
"""CP — Home Audio: zones, groups, streams, volume, mute, latency, server handoff, refresh, offline, partial failure."""

from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge

pytestmark = pytest.mark.isolation


class TestHomeAudioEnhanced:
    @pytest.fixture
    def mock_ha(self):
        ha = MagicMock()
        ha.is_connected = True
        type(ha).is_connected = PropertyMock(return_value=True)
        ha.test_connection.return_value = True
        ha.get_devices.return_value = [
            {"name": "Living Room", "entity_id": "media_player.living_room"},
            {"name": "Kitchen", "entity_id": "media_player.kitchen"},
        ]
        return ha

    @pytest.fixture
    def mock_snapcast(self):
        sc = MagicMock()
        sc.is_available = True
        type(sc).is_available = PropertyMock(return_value=True)
        sc.get_groups.return_value = [
            {"id": "g1", "name": "Living Room", "muted": False, "volume": 80},
            {"id": "g2", "name": "Kitchen", "muted": True, "volume": 30},
        ]
        return sc

    @pytest.fixture
    def bridge(self, mock_ha, mock_snapcast):
        return HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=mock_snapcast)

    def test_initial_state(self, bridge):
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.snapcastState == "unavailable"

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

    def test_refresh_sets_snapcast_available(self, bridge):
        bridge.refresh()
        assert bridge.snapcastState == "available"

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

    def test_set_zone_volume(self, bridge, mock_snapcast):
        result = bridge.setZoneVolume("g1", 0.75)
        assert result["ok"] is True

    def test_set_zone_volume_no_snapcast(self):
        b = HomeAudioBridge()
        result = b.setZoneVolume("g1", 0.5)
        assert result["ok"] is False

    def test_set_zone_mute(self, bridge, mock_snapcast):
        result = bridge.setZoneMute("g1", True)
        assert result["ok"] is True

    def test_set_zone_mute_no_snapcast(self):
        b = HomeAudioBridge()
        result = b.setZoneMute("g1", True)
        assert result["ok"] is False

    def test_assign_stream(self, bridge, mock_snapcast):
        result = bridge.assignStream("stream_main")
        assert result["ok"] is True

    def test_assign_stream_no_snapcast(self):
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

    def test_no_snapcast_concept_state(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        b.refresh()
        assert b.snapcastState == "concept"

    def test_capabilities(self, bridge):
        assert bridge.homeAssistantAvailable is True
        assert bridge.snapcastAvailable is True
        assert bridge.zonesSupported is True
        assert bridge.volumeSupported is True

    def test_open_diagnostics(self, bridge):
        result = bridge.openDiagnostics()
        assert result["ok"] is True
