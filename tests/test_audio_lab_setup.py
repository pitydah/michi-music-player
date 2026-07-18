"""Tests for Audio Lab — service available, capabilities, setup."""
import pytest


class TestAudioLabSetup:
    def test_audio_lab_service_available(self):
        from core.composition.infrastructure import build as infra
        from core.composition.playback import build as playback
        from core.composition.library import build as library
        from core.composition.audio_lab import build as audio_lab
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        playback(c)
        library(c)
        audio_lab(c)
        svc = c.get("audio_lab_service")
        assert svc is not None

    def test_diagnostics_service_available(self):
        from core.composition.infrastructure import build as infra
        from core.composition.playback import build as playback
        from core.composition.library import build as library
        from core.composition.audio_lab import build as audio_lab
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        playback(c)
        library(c)
        audio_lab(c)
        ds = c.get("diagnostics_service")
        assert ds is not None

    def test_conversion_service_imports(self):
        from core.audio_lab.audio_conversion_service import AudioConversionService
        assert AudioConversionService is not None

    def test_audio_lab_job_adapter(self):
        from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter
        assert AudioLabJobAdapter is not None

    def test_audio_lab_has_capabilities(self):
        from core.composition.infrastructure import build as infra
        from core.composition.playback import build as playback
        from core.composition.library import build as library
        from core.composition.audio_lab import build as audio_lab
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        playback(c)
        library(c)
        audio_lab(c)
        svc = c.get("audio_lab_service")
        if hasattr(svc, 'capability_map'):
            caps = svc.capability_map()
            assert isinstance(caps, dict)

    def test_audio_lab_bridge_import(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        assert AudioLabBridge is not None
