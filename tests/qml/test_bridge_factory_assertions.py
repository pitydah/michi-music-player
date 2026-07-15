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
    def test_settings_identity(self):
        f = BridgeFactory(_make_container())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]

    def test_settings_identity_fails(self):
        f = BridgeFactory(_make_container())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = MagicMock()
        assert f._bridges["settings"] is not f._bridges["settings_v2"]

    def test_create_all_creates_shared_settings(self):
        c = _make_container()
        f = BridgeFactory(c)
        created = f.create_all()
        assert created["settings"] is created["settings_v2"]
