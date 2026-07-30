"""Tests for BridgeFactory wiring assertions."""
from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory
from core.service_container import ServiceContainer


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    for k, v in {
        "playback_service": MagicMock(),
        "worker_manager": MagicMock(),
        "database": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "global_search_service": MagicMock(),
        "track_action_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "notification_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "job_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "playlist_service": MagicMock(),
        "queue_service": MagicMock(),
        "history_query_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "connection_service": MagicMock(),
        "radio_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "metadata_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "process_controller": MagicMock(),
    }.items():
        c.register(k, overrides.get(k, v))
    return c


class TestSettingsIdentity:
    def test_create_all_creates_settings(self):
        c = _make_container()
        f = BridgeFactory(c)
        created = f.create_all()
        assert "settings" in created


class TestCoverProviderIdentity:
    def test_create_all_wires_cover_provider_into_nowplaying(self):
        c = _make_container(artwork_service=MagicMock())
        c.register("artwork_service", MagicMock())
        f = BridgeFactory(c)

        created = f.create_all()

        assert created["nowplaying"]._cover_provider is created["cover_provider"]
