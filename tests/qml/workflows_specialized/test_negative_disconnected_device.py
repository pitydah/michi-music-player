"""MX: Negative — disconnected device scenarios."""
from __future__ import annotations

from ui_qml_bridge.devices_bridge import DevicesBridge
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


def test_devices_disconnected_no_peers():
    bridge = DevicesBridge(sync_manager=None)
    assert len(bridge.peers) == 0


def test_home_audio_disconnected_ha():
    bridge = HomeAudioBridge(ha_controller=None)
    assert bridge.homeAssistantAvailable is False
    assert bridge.snapcastAvailable is False


def test_home_audio_no_devices():
    bridge = HomeAudioBridge(ha_controller=None)
    assert len(bridge.devices) == 0
    assert len(bridge.zones) == 0


def test_devices_no_transfer_jobs():
    bridge = DevicesBridge(sync_manager=None)
    assert bridge.transferJobs is None or len(bridge.transferJobs) == 0
