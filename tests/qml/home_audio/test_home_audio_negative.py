"""Negative tests for Home Audio: null bridge, errors, edge cases."""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest
pytestmark = pytest.mark.isolation


class TestDegradedState:
    @pytest.fixture
    def degraded_ha(self):
        ha = MagicMock()
        ha.is_connected = True
        type(ha).is_connected = PropertyMock(return_value=True)
        ha.get_devices = MagicMock(side_effect=Exception("HA unavailable"))
        ha.reconnect = MagicMock(return_value=False)
        ha.test_connection.return_value = False
        return ha

    @pytest.fixture
    def bridge(self, degraded_ha):
        return HomeAudioBridge(home_audio_service=degraded_ha)

    def test_degraded_ha_state(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "error"

    def test_degraded_has_error_message(self, bridge):
        bridge.refresh()
        assert bridge.lastError != ""

    def test_degraded_zones_empty(self, bridge):
        bridge.refresh()
        assert bridge.zones == []

    def test_degraded_devices_empty(self, bridge):
        bridge.refresh()
        assert bridge.devices == []

    def test_degraded_reconnect_fails(self, bridge):
        result = bridge.reconnectHa()
        assert result["ok"] is False

    def test_degraded_configure_fails(self, bridge):
        result = bridge.configureHomeAssistant("host", 8123, "token")
        assert result["ok"] is False


class TestOfflineZones:
    @pytest.fixture
    def offline_ha(self):
        ha = MagicMock()
        ha.is_connected = False
        type(ha).is_connected = PropertyMock(return_value=False)
        ha.get_devices.return_value = []
        ha.reconnect = MagicMock(return_value=False)
        ha.test_connection = MagicMock(return_value=False)
        return ha

    @pytest.fixture
    def bridge(self, offline_ha):
        return HomeAudioBridge(home_audio_service=offline_ha)

    def test_offline_state(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "not_configured"

    def test_offline_no_devices(self, bridge):
        bridge.refresh()
        assert bridge.devices == []

    def test_offline_no_zones(self, bridge):
        bridge.refresh()
        assert bridge.zones == []

    def test_offline_no_contact(self, bridge):
        bridge.refresh()
        assert bridge.lastContact == 0.0

    def test_offline_reconnect_fails(self, bridge):
        result = bridge.reconnectHa()
        assert result["ok"] is False

    def test_offline_disconnect(self, bridge):
        bridge.disconnectHa()
        assert bridge.homeAssistantState == "not_configured"


class TestPartialFailure:
    @pytest.fixture
    def partial_ha(self):
        ha = MagicMock()
        ha.is_connected = True
        type(ha).is_connected = PropertyMock(return_value=True)
        ha.get_devices = MagicMock(side_effect=Exception("Devices unavailable"))
        ha.reconnect = MagicMock()
        ha.set_volume = MagicMock()
        ha.set_mute = MagicMock()
        return ha

    @pytest.fixture
    def bridge(self, partial_ha):
        return HomeAudioBridge(home_audio_service=partial_ha)

    def test_partial_devices_empty(self, bridge):
        bridge.refresh()
        assert bridge.devices == []

    def test_partial_ha_state_error(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "error"

    def test_volume_unsupported_when_no_ctrl(self):
        b = HomeAudioBridge()
        assert b.volumeSupported is False

    def test_partial_error_message_set(self, bridge):
        bridge.refresh()
        assert bridge.lastError != ""
