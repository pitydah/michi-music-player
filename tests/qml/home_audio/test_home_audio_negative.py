"""Negative tests for Home Audio: null bridge, errors, edge cases."""
from unittest.mock import MagicMock, PropertyMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge

pytestmark = pytest.mark.isolation


class TestHomeAudioNegative:
    def test_null_bridge_safe_refresh(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        result = b.refresh()
        assert result["ok"] is True

    def test_null_bridge_configure(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.configureHomeAssistant("host", 8123, "token")
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_null_bridge_set_volume(self):
        b = HomeAudioBridge()
        result = b.setZoneVolume("zone1", 0.5)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_null_bridge_set_mute(self):
        b = HomeAudioBridge()
        result = b.setZoneMute("zone1", True)
        assert result["ok"] is False

    def test_null_bridge_assign_stream(self):
        b = HomeAudioBridge()
        result = b.assignStream("stream_main")
        assert result["ok"] is False

    def test_null_bridge_discover_receivers(self):
        b = HomeAudioBridge()
        result = b.discoverReceivers()
        assert result["ok"] is False

    def test_null_ha_reconnect(self):
        b = HomeAudioBridge(ha_controller=None)
        result = b.reconnectHa()
        assert result["ok"] is False

    def test_partial_failure_marks_error(self):
        mock_ha = MagicMock()
        mock_ha.is_connected = True
        type(mock_ha).is_connected = PropertyMock(return_value=True)
        mock_ha.get_devices = MagicMock(side_effect=Exception("HA error"))
        b = HomeAudioBridge(ha_controller=mock_ha, snapcast_ctrl=None)
        b.refresh()
        assert b.homeAssistantState == "error" or b.lastError != ""

    def test_snapcast_failure_does_not_crash(self):
        mock_snap = MagicMock()
        mock_snap.is_available = True
        type(mock_snap).is_available = PropertyMock(return_value=True)
        mock_snap.get_groups = MagicMock(side_effect=Exception("Snapcast error"))
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=mock_snap)
        b.refresh()
        assert b.snapcastState != "available"

    def test_offline_state(self):
        b = HomeAudioBridge(ha_controller=None, snapcast_ctrl=None)
        b._offline = True
        assert b.offline is True

    def test_servers_not_available(self):
        b = HomeAudioBridge()
        assert b.snapcastAvailable is False
        assert b.zonesSupported is False
        assert b.groupingSupported is False

    def test_volume_unsupported_when_no_ctrl(self):
        b = HomeAudioBridge()
        assert b.volumeSupported is False
