<<<<<<< Updated upstream
"""Test negative cases: degraded state, offline zones, partial failure."""
=======
<<<<<<< HEAD
"""Negative tests for Home Audio: null bridge, errors, edge cases."""
>>>>>>> Stashed changes
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
        return HomeAudioBridge(ha_controller=degraded_ha, snapcast_ctrl=None)

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
        assert result["ok"] is True


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
        return HomeAudioBridge(ha_controller=offline_ha, snapcast_ctrl=None)

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
    def partial_snap(self):
        sc = MagicMock()
        sc.is_available = False
        type(sc).is_available = PropertyMock(return_value=False)
        sc.get_groups = MagicMock(side_effect=Exception("Snapcast unavailable"))
        return sc

    @pytest.fixture
    def bridge(self, partial_ha, partial_snap):
        return HomeAudioBridge(ha_controller=partial_ha, snapcast_ctrl=partial_snap)

    def test_partial_devices_empty(self, bridge):
        bridge.refresh()
        assert bridge.devices == []

    def test_partial_ha_state_error(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "error"

<<<<<<< Updated upstream
=======
    def test_volume_unsupported_when_no_ctrl(self):
        b = HomeAudioBridge()
        assert b.volumeSupported is False
=======
"""Test negative cases: degraded state, offline zones, partial failure."""
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
        return HomeAudioBridge(ha_controller=degraded_ha, snapcast_ctrl=None)

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
        assert result["ok"] is True


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
        return HomeAudioBridge(ha_controller=offline_ha, snapcast_ctrl=None)

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
    def partial_snap(self):
        sc = MagicMock()
        sc.is_available = False
        type(sc).is_available = PropertyMock(return_value=False)
        sc.get_groups = MagicMock(side_effect=Exception("Snapcast unavailable"))
        return sc

    @pytest.fixture
    def bridge(self, partial_ha, partial_snap):
        return HomeAudioBridge(ha_controller=partial_ha, snapcast_ctrl=partial_snap)

    def test_partial_devices_empty(self, bridge):
        bridge.refresh()
        assert bridge.devices == []

    def test_partial_ha_state_error(self, bridge):
        bridge.refresh()
        assert bridge.homeAssistantState == "error"

>>>>>>> Stashed changes
    def test_partial_error_message_set(self, bridge):
        bridge.refresh()
        assert bridge.lastError != ""

    def test_partial_volume_uses_snapcast(self, bridge, partial_snap):
        result = bridge.setZoneVolume("z1", 0.5)
        assert result["ok"] is True
        assert partial_snap.set_group_volume.called

    def test_partial_mute_uses_snapcast(self, bridge, partial_snap):
        result = bridge.setZoneMute("z1", True)
        assert result["ok"] is True
        assert partial_snap.set_group_mute.called

    def test_partial_group_unsupported(self, bridge):
        result = bridge.groupZones("z1,z2")
        assert result["ok"] is True

    def test_partial_ungroup_unsupported(self, bridge):
        result = bridge.ungroupZone("z1")
        assert result["ok"] is True

    def test_partial_disconnect_resets(self, bridge):
        bridge.disconnectHa()
        assert bridge.devices == []
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
