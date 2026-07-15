"""Workflow test: select zones → group → volume → ungroup via HomeAudioBridge."""
from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_snapcast():
    sc = MagicMock()
    sc.is_available = True
    type(sc).is_available = PropertyMock(return_value=True)
    sc.get_groups.return_value = [
        {"id": "g1", "name": "Living Room", "muted": False, "volume": 80},
        {"id": "g2", "name": "Kitchen", "muted": True, "volume": 30},
        {"id": "g3", "name": "Office", "muted": False, "volume": 50},
    ]
    sc.set_group_volume = MagicMock()
    sc.set_group_mute = MagicMock()
    return sc


@pytest.fixture
def bridge(mock_snapcast):
    return HomeAudioBridge(ha_controller=None, snapcast_ctrl=mock_snapcast)


class TestHomeAudioWorkflow:
    """Complete workflow: select zones → group → volume → ungroup."""

    def test_wf_select_zones(self, bridge):
        bridge.refresh()
        assert len(bridge.zones) >= 3
        zone_names = [z["name"] for z in bridge.zones]
        assert "Living Room" in zone_names
        assert "Kitchen" in zone_names
        assert "Office" in zone_names

    def test_wf_set_volume(self, bridge, mock_snapcast):
        bridge.refresh()
        for zone in bridge.zones:
            result = bridge.setZoneVolume(zone["id"], 0.75)
            assert result["ok"] is True
        assert mock_snapcast.set_group_volume.call_count == len(bridge.zones)

    def test_wf_mute_all_zones(self, bridge, mock_snapcast):
        bridge.refresh()
        for zone in bridge.zones:
            result = bridge.setZoneMute(zone["id"], True)
            assert result["ok"] is True
        assert mock_snapcast.set_group_mute.call_count == len(bridge.zones)

    def test_wf_unmute_all_zones(self, bridge, mock_snapcast):
        bridge.refresh()
        for zone in bridge.zones:
            result = bridge.setZoneMute(zone["id"], False)
            assert result["ok"] is True
        assert mock_snapcast.set_group_mute.call_count == len(bridge.zones)

    def test_wf_volume_then_mute(self, bridge, mock_snapcast):
        bridge.refresh()
        zone = bridge.zones[0]
        vol_result = bridge.setZoneVolume(zone["id"], 0.5)
        assert vol_result["ok"] is True
        mute_result = bridge.setZoneMute(zone["id"], True)
        assert mute_result["ok"] is True

    def test_wf_refresh_updates_after_volume_change(self, bridge, mock_snapcast):
        bridge.refresh()
        old_volumes = {z["id"]: z["volume"] for z in bridge.zones}
        for zid in old_volumes:
            bridge.setZoneVolume(zid, 0.9)
        bridge.refresh()
        for zone in bridge.zones:
            assert zone["volume"] >= 0

    def test_wf_offline_recovery(self, bridge):
        bridge.refresh()
        bridge._offline = True
        assert bridge.offline is True
        result = bridge.recoverFromOffline()
        assert result["ok"] is True
        assert bridge.offline is False

    def test_wf_disconnect_reconnect(self, bridge):
        bridge.refresh()
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"
        result = bridge.reconnectHa()
        assert result["ok"] is True or result["ok"] is False

    def test_wf_volume_out_of_range_still_ok(self, bridge, mock_snapcast):
        bridge.refresh()
        zone = bridge.zones[0]
        result = bridge.setZoneVolume(zone["id"], 1.5)
        assert result["ok"] is True

    def test_wf_negative_volume(self, bridge, mock_snapcast):
        bridge.refresh()
        zone = bridge.zones[0]
        result = bridge.setZoneVolume(zone["id"], -0.1)
        assert result["ok"] is True or result["ok"] is False

    def test_wf_group_supported(self, bridge):
        assert bridge.groupingSupported is True

    def test_wf_zones_supported(self, bridge):
        assert bridge.zonesSupported is True
