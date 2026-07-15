"""Home Audio workflow through the current service/bridge contract."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.home_audio_bridge import HomeAudioBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def service():
    svc = MagicMock()
    svc.available = True
    svc.ha_available = True
    svc.snapcast_available = True
    svc.is_connected = True
    svc.latency_ms = 12
    svc.get_zones.return_value = [
        {"id": "zone1", "name": "Living Room"},
        {"id": "zone2", "name": "Kitchen"},
        {"id": "zone3", "name": "Bedroom"},
    ]
    svc.get_devices.return_value = [
        {"name": "Living Room Speaker", "entity_id": "media_player.living_room"},
        {"name": "Kitchen Speaker", "entity_id": "media_player.kitchen"},
    ]
    svc.get_groups.return_value = []
    svc.get_streams.return_value = []
    svc.group.return_value = {"ok": True, "group_id": "group1"}
    svc.ungroup.return_value = {"ok": True}
    svc.set_volume.return_value = {"ok": True}
    svc.set_mute.return_value = {"ok": True}
    return svc


@pytest.fixture
def bridge(service):
    return HomeAudioBridge(home_audio_service=service)


def test_refresh_discovers_real_service_state(bridge):
    assert bridge.refresh()["ok"] is True
    assert bridge.homeAssistantState == "connected"
    assert len(bridge.zones) == 3
    assert len(bridge.devices) == 2


def test_group_volume_mute_and_ungroup(bridge, service):
    assert bridge.groupZones("zone1,zone2")["ok"] is True
    assert bridge.setZoneVolume("group1", 0.75)["ok"] is True
    assert bridge.setZoneMute("group1", False)["ok"] is True
    assert bridge.ungroupZone("group1")["ok"] is True
    service.group.assert_called_once_with("zone1,zone2")
    service.set_volume.assert_called_once_with("group1", 0.75)
    service.set_mute.assert_called_once_with("group1", False)
    service.ungroup.assert_called_once_with("group1")


def test_disconnect_clears_qml_state(bridge):
    bridge.refresh()
    assert bridge.disconnectHa()["ok"] is True
    assert bridge.homeAssistantState == "not_configured"
    assert bridge.devices == []


def test_missing_service_reports_capability_unavailable():
    bridge = HomeAudioBridge()
    assert bridge.groupZones("zone1")["ok"] is False
    assert bridge.receiversAvailable is False
