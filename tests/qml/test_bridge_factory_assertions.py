"""Tests for BridgeFactory wiring assertions."""
from unittest.mock import MagicMock

from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle


def _make_bundle(**overrides) -> ServiceBundle:
    b = ServiceBundle()
    for k, v in {
        "player_service": MagicMock(),
        "db": MagicMock(),
        "db_connection": MagicMock(),
        "search_engine": MagicMock(),
        "radio_manager": MagicMock(),
        "sync_manager": MagicMock(),
        "michi_link_controller": MagicMock(),
        "home_audio_controller": MagicMock(),
        "snapcast_controller": MagicMock(),
        "disc_service": MagicMock(),
        "worker_manager": MagicMock(),
        "metadata_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "queue_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "notification_service": MagicMock(),
        "action_registry": MagicMock(),
        "history_query_service": MagicMock(),
        "global_search_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "job_service": MagicMock(),
    }.items():
        setattr(b, k, overrides.get(k, v))
    return b


class TestSettingsIdentity:
    def test_settings_identity(self):
        f = BridgeFactory(_make_bundle())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = f._bridges["settings"]

    def test_settings_identity_fails(self):
        f = BridgeFactory(_make_bundle())
        f._bridges["settings"] = MagicMock()
        f._bridges["settings_v2"] = MagicMock()
        assert f._bridges["settings"] is not f._bridges["settings_v2"]

    def test_create_all_creates_shared_settings(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        created = f.create_all()
        assert created["settings"] is created["settings_v2"]
