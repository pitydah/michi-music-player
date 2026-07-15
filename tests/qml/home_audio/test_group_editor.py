"""Test group creation/editing through HomeAudioBridge."""
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
import pytest

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_ha_svc():
    ha = MagicMock()
    ha.is_connected = True
    type(ha).is_connected = PropertyMock(return_value=True)
    ha.get_zones.return_value = [
        {"id": "z1", "name": "Living Room", "volume": 80, "muted": False},
        {"id": "z2", "name": "Kitchen", "volume": 50, "muted": True},
        {"id": "z3", "name": "Bedroom", "volume": 30, "muted": False},
    ]
    ha.get_groups.return_value = []
    ha.get_devices.return_value = []
    ha.get_streams.return_value = []
    ha.group = MagicMock()
    ha.ungroup = MagicMock()
    ha.set_group_name = MagicMock()
    ha.delete_group = MagicMock()
    return ha


@pytest.fixture
def bridge(mock_ha_svc):
    return HomeAudioBridge(home_audio_service=mock_ha_svc)


class TestGroupCreation:
    def test_group_zones_valid(self, bridge, mock_ha_svc):
        result = bridge.groupZones("z1,z2")
        assert result["ok"] is True
        assert mock_ha_svc.group.called

    def test_group_zones_empty_fails(self, bridge):
        result = bridge.groupZones("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONES"

    def test_group_zones_single(self, bridge):
        result = bridge.groupZones("z1")
        assert result["ok"] is True

    def test_ungroup_valid(self, bridge, mock_ha_svc):
        result = bridge.ungroupZone("z1")
        assert result["ok"] is True
        assert mock_ha_svc.ungroup.called

    def test_ungroup_empty_fails(self, bridge):
        result = bridge.ungroupZone("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_ZONE"

    def test_rename_zone_valid(self, bridge, mock_ha_svc):
        result = bridge.renameZone("z1", "New Name")
        assert result["ok"] is True
        assert mock_ha_svc.set_group_name.called

    def test_rename_zone_empty_fails(self, bridge):
        result = bridge.renameZone("", "New")
        assert result["ok"] is False

    def test_rename_zone_empty_name_fails(self, bridge):
        result = bridge.renameZone("z1", "")
        assert result["ok"] is False

    def test_delete_zone_valid(self, bridge, mock_ha_svc):
        result = bridge.deleteZone("z1")
        assert result["ok"] is True
        assert mock_ha_svc.delete_group.called

    def test_delete_zone_empty_fails(self, bridge):
        result = bridge.deleteZone("")
        assert result["ok"] is False


class TestGroupNoController:
    def test_group_unsupported(self):
        b = HomeAudioBridge()
        result = b.groupZones("z1,z2")
        assert result["ok"] is False

    def test_ungroup_unsupported(self):
        b = HomeAudioBridge()
        result = b.ungroupZone("z1")
        assert result["ok"] is False

    def test_rename_unsupported(self):
        b = HomeAudioBridge()
        result = b.renameZone("z1", "New")
        assert result["ok"] is False

    def test_delete_unsupported(self):
        b = HomeAudioBridge()
        result = b.deleteZone("z1")
        assert result["ok"] is False


class TestGroupsProperty:
    def test_groups_populated(self, bridge):
        bridge.refresh()
        assert bridge.groups is not None

    def test_groups_list(self, bridge):
        bridge.refresh()
        assert isinstance(bridge.groups, list)
