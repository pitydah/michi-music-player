"""Tests for Home Audio — Snapcast, HA adapter, handoff."""
from unittest.mock import MagicMock, patch

import pytest


class TestHomeAudioService:
    def test_service_import(self):
        from core.home_audio_service import HomeAudioService
        assert HomeAudioService is not None

    def test_snapcast_adapter_import(self):
        from ui_qml_bridge.adapters.snapcast_adapter import SnapcastAdapter
        assert SnapcastAdapter is not None

    def test_home_audio_adapter_import(self):
        from ui_qml_bridge.adapters.home_audio_adapter import HomeAudioAdapter
        assert HomeAudioAdapter is not None

    def test_home_audio_bridge_import(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert HomeAudioBridge is not None

    def test_home_audio_bridge_signals(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'stateChanged')

    def test_home_audio_snapcast_discovery(self):
        from integrations.snapcast.discovery import SnapClientDiscovery
        disc = SnapClientDiscovery()
        assert hasattr(disc, 'clients') and hasattr(disc, 'refresh')

    def test_home_audio_bridge_has_groups(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'groupZones')

    def test_home_audio_bridge_volume(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        assert hasattr(HomeAudioBridge, 'setZoneVolume')
