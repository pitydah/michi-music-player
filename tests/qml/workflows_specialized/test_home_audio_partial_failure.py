"""MN: Test HomeAudioBridge — partial failure, degraded state, one fails others work."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


@pytest.fixture
def ha_ctrl():
    ctrl = MagicMock()
    ctrl.is_connected = lambda: True
    ctrl.get_devices.return_value = [{"name": "Speaker 1", "entity_id": "media_player.speaker_1"}]
    return ctrl


@pytest.fixture
def snapcast_ctrl():
    ctrl = MagicMock()
    ctrl.is_available = True
    ctrl.get_groups.return_value = [
        {"id": "zone1", "name": "Living Room", "muted": False, "volume": 80},
        {"id": "zone2", "name": "Kitchen", "muted": False, "volume": 50},
    ]
    return ctrl


@pytest.fixture
def bridge_ha_only(ha_ctrl):
    return HomeAudioBridge(ha_controller=ha_ctrl)


@pytest.fixture
def bridge_snap_only(snapcast_ctrl):
    return HomeAudioBridge(snapcast_ctrl=snapcast_ctrl)


@pytest.fixture
def bridge_full(ha_ctrl, snapcast_ctrl):
    return HomeAudioBridge(ha_controller=ha_ctrl, snapcast_ctrl=snapcast_ctrl)


class TestHomeAudioPartialFailure:
    def test_no_controllers_both_unavailable(self):
        b = HomeAudioBridge()
        b.refresh()
        assert b.homeAssistantAvailable is False
        assert b.snapcastAvailable is False

    def test_ha_fails_snapcast_works(self, snapcast_ctrl):
        failing_ha = MagicMock()
        def _raise_conn():
            raise Exception("Connection refused")
        failing_ha.is_connected = _raise_conn
        b = HomeAudioBridge(ha_controller=failing_ha, snapcast_ctrl=snapcast_ctrl)
        b.refresh()
        assert b.snapcastState == "available"
        assert b.lastError != ""

    def test_snapcast_fails_ha_works(self, ha_ctrl):
        failing_snap = MagicMock()
        failing_snap.is_available = True
        failing_snap.get_groups.side_effect = Exception("Snapcast timeout")
        b = HomeAudioBridge(ha_controller=ha_ctrl, snapcast_ctrl=failing_snap)
        b.refresh()
        assert b.homeAssistantState == "connected"
        assert b.lastError != ""

    def test_both_fail_reports_last_error(self):
        failing_ha = MagicMock()
        def _raise_ha():
            raise Exception("HA down")
        failing_ha.is_connected = _raise_ha
        failing_snap = MagicMock()
        def _raise_snap():
            raise Exception("Snap down")
        failing_snap.is_available = _raise_snap
        b = HomeAudioBridge(ha_controller=failing_ha, snapcast_ctrl=failing_snap)
        b.refresh()
        assert b.lastError != ""

    def test_ha_connected_shows_devices(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        b.refresh()
        assert b.homeAssistantState == "connected"
        assert len(b.devices) > 0

    def test_snapcast_available_shows_zones(self, snapcast_ctrl):
        b = HomeAudioBridge(snapcast_ctrl=snapcast_ctrl)
        b.refresh()
        assert b.snapcastState == "available"
        assert len(b.zones) > 0

    def test_volume_supported_with_at_least_one_ctrl(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        assert b.volumeSupported is True

    def test_volume_not_supported_without_controllers(self):
        b = HomeAudioBridge()
        assert b.volumeSupported is False

    def test_zones_not_supported_without_snapcast(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        assert b.zonesSupported is False

    def test_zones_supported_with_snapcast(self, snapcast_ctrl):
        b = HomeAudioBridge(snapcast_ctrl=snapcast_ctrl)
        assert b.zonesSupported is True

    def test_set_zone_volume_without_snapcast_returns_error(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.setZoneVolume("zone1", 0.5)
        assert result.get("error") == "UNSUPPORTED"

    def test_set_zone_volume_with_snapcast_calls_ctrl(self, snapcast_ctrl):
        snapcast_ctrl.set_group_volume = MagicMock()
        b = HomeAudioBridge(snapcast_ctrl=snapcast_ctrl)
        result = b.setZoneVolume("zone1", 0.8)
        assert result.get("ok") is True
        snapcast_ctrl.set_group_volume.assert_called_once_with("zone1", 0.8)

    def test_refresh_does_not_raise_with_partial_controllers(self):
        b = HomeAudioBridge()
        try:
            b.refresh()
        except Exception:
            pytest.fail("refresh raised exception with partial controllers")

    def test_disconnect_ha_resets_state(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        b.refresh()
        assert b.homeAssistantState == "connected"
        b.disconnectHa()
        assert b.homeAssistantState == "not_configured"
        assert len(b.devices) == 0

    def test_group_zones_without_snapcast(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.groupZones("zone1,zone2")
        assert result.get("error") == "UNSUPPORTED"

    def test_group_zones_with_snapcast_calls_ctrl(self, snapcast_ctrl):
        snapcast_ctrl.group = MagicMock()
        b = HomeAudioBridge(snapcast_ctrl=snapcast_ctrl)
        result = b.groupZones("zone1,zone2")
        assert result.get("ok") is True
        snapcast_ctrl.group.assert_called_once()

    def test_ungroup_without_snapcast(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.ungroupZone("zone1")
        assert result.get("error") == "UNSUPPORTED"

    def test_rename_zone_without_snapcast(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.renameZone("zone1", "New Name")
        assert result.get("error") == "UNSUPPORTED"

    def test_delete_zone_without_snapcast(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.deleteZone("zone1")
        assert result.get("error") == "UNSUPPORTED"

    def test_receivers_available_is_false(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        assert b.receiversAvailable is False

    def test_discover_receivers_returns_unsupported(self, ha_ctrl):
        b = HomeAudioBridge(ha_controller=ha_ctrl)
        result = b.discoverReceivers()
        assert result.get("error") == "UNSUPPORTED"
