"""Tests for Home Audio — handoff, Snapcast, HA, zone groups."""

import inspect

import pytest


class TestHomeAudioHandoff:
    def test_home_audio_service_import(self):
        from core.home_audio_service import HomeAudioService
        assert HomeAudioService is not None

    def test_snapcast_group_manager_import(self):
        try:
            from integrations.snapcast.group_manager import GroupManager
            assert GroupManager is not None
        except ImportError:
            pytest.skip("Snapcast integrations not available")

    def test_home_assistant_adapter_import(self):
        try:
            from integrations.connections.adapters.home_assistant_adapter import HomeAssistantAdapter
            assert HomeAssistantAdapter is not None
        except ImportError:
            pytest.skip("HA adapter not available")

    def test_bridge_handoff_removed(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert not hasattr(HomeAudioBridge, 'handoffToServer')
        assert not hasattr(HomeAudioBridge, 'serverHandoff')

    def test_service_handoff_is_not_implemented(self):
        from core.home_audio_service import HomeAudioService

        parameters = inspect.signature(HomeAudioService.__init__).parameters

        assert "local_media_server" not in parameters
        assert not hasattr(HomeAudioService, "server_handoff_available")
        assert not hasattr(HomeAudioService, "server_handoff")
        assert not hasattr(HomeAudioService, "handoff")

    def test_bridge_group_operations(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'groupZones')

    def test_bridge_volume_operations(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'setZoneVolume')

    def test_bridge_discover(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'discoverReceivers')

    def test_home_audio_composition(self):
        from core.composition.infrastructure import build as infra
        from core.composition.ecosystem import build as eco
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        eco(c)
        ha = c.get("home_audio_service")
        assert ha is not None
