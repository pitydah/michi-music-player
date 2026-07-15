from __future__ import annotations
"""MX: Negative — service unavailable for each specialized domain."""

def test_devices_no_sync_manager():
    from ui_qml_bridge.devices_bridge import DevicesBridge
    bridge = DevicesBridge(sync_manager=None)
    result = bridge.startServer()
    assert result.get("ok") is False
    assert "NO_SYNC_MANAGER" in result.get("error", "")


def test_mix_no_db():
    from ui_qml_bridge.mix_bridge import MixBridge
    bridge = MixBridge()
    assert len(bridge.categories) > 0
    result = bridge.loadMix("favorites")
    assert result.get("ok") is False


def test_radio_no_radio_manager():
    from ui_qml_bridge.radio_bridge import RadioBridge
    bridge = RadioBridge(radio_manager=None)
    result = bridge.refresh()
    assert result.get("ok") is True
    assert len(bridge.stations) == 0


def test_global_search_no_search_service():
    from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
    bridge = GlobalSearchBridge(search_service=None)
    result = bridge.search("test")
    assert result.get("ok") is False


def test_connections_no_controller():
    from ui_qml_bridge.connections_bridge import ConnectionsBridge
    bridge = ConnectionsBridge(michi_link_ctrl=None)
    result = bridge.refresh()
    assert result.get("ok") is True


def test_home_audio_no_controller():
    from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
    bridge = HomeAudioBridge(ha_controller=None)
    assert bridge.homeAssistantAvailable is False


def test_notifications_bridge_loads():
    from ui_qml_bridge.notification_bridge import NotificationBridge
    bridge = NotificationBridge()
    assert bridge.currentNotification is None
    assert bridge.queueLength == 0


def test_capability_guard_no_bridge():
    filepath = "ui_qml/components/CapabilityGuard.qml"
    with open(filepath) as f:
        content = f.read()
    assert "!bridge" in content
