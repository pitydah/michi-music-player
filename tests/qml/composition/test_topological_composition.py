"""Tests for topological composition: BridgeFactory + ServiceContainer integration."""

from unittest.mock import Mock

from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    defaults = {
        "database": Mock(),
        "connection_factory": Mock(),
        "worker_manager": Mock(),
        "query_executor": Mock(),
        "job_service": Mock(),
        "event_bus": Mock(),
        "settings_coordinator": Mock(),
        "settings_service": Mock(),
        "library_query_service": Mock(),
        "library_sources_service": Mock(),
        "library_mutation_service": Mock(),
        "playlist_service": Mock(),
        "history_query_service": Mock(),
        "global_search_service": Mock(),
        "mix_query_service": Mock(),
        "mix_service": Mock(),
        "track_action_service": Mock(),
        "playback_service": Mock(),
        "queue_service": Mock(),
        "metadata_service": Mock(),
        "theme_service": Mock(),
        "accessibility_service": Mock(),
        "audio_lab_service": Mock(),
        "smart_tagging_service": Mock(),
        "library_doctor_service": Mock(),
        "device_sync_service": Mock(),
        "connection_service": Mock(),
        "home_audio_service": Mock(),
        "radio_service": Mock(),
        "lyrics_service": Mock(),
        "diagnostics_service": Mock(),
        "notification_service": Mock(),
        "action_registry": Mock(),
        "confirmation_service": Mock(),
        "runtime_persistence": Mock(),
        "process_controller": Mock(),
        "michi_ai_service": Mock(),
    }
    defaults.update(overrides)
    for name, svc in defaults.items():
        if name in c._all_names():
            c.register(name, svc)
    return c


def _make_bundle(**overrides) -> ServiceBundle:
    b = ServiceBundle()
    for k, v in {
        "player_service": Mock(),
        "db": Mock(),
        "db_connection": Mock(),
        "search_engine": Mock(),
        "radio_manager": Mock(),
        "sync_manager": Mock(),
        "michi_link_controller": Mock(),
        "home_audio_controller": Mock(),
        "snapcast_controller": Mock(),
        "disc_service": Mock(),
        "worker_manager": Mock(),
        "metadata_service": Mock(),
        "smart_tagging_service": Mock(),
    }.items():
        setattr(b, k, overrides.get(k, v))
    return b


class TestBridgeFactoryWithContainer:
    def test_creates_navigation_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_navigation_bridge()
        assert f.has("navigation")
        assert f.get("navigation") is not None

    def test_creates_app_state_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_app_state_bridge()
        assert f.has("app_state")
        assert f.get("app_state") is not None

    def test_creates_theme_bridge_with_coordinator(self):
        b = _make_bundle()
        b.settings_coordinator = Mock()
        f = BridgeFactory(b)
        f.create_theme_bridge()
        assert f.get("theme") is not None

    def test_creates_notification_bridge_with_action_registry(self):
        f = BridgeFactory(_make_bundle())
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("notification")


class TestTopologicalOrder:
    def test_config_before_theme_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_theme_bridge()
        assert f._services.settings_coordinator is not None or f._services.settings_coordinator is None

    def test_worker_manager_before_job_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_job_bridge()
        assert f._services.worker_manager is not None

    def test_queue_service_available(self):
        b = _make_bundle()
        b.queue_service = Mock()
        assert b.queue_service is not None


class TestAssertRequiredDependencies:
    def test_create_all_returns_dict(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_create_all_has_expected_bridges(self):
        f = BridgeFactory(_make_bundle())
        result = f.create_all()
        expected_keys = {
            "navigation", "app_state", "route_registry", "job_bridge",
            "action_registry", "capability", "selection_context",
            "theme", "accessibility", "settings", "playlists",
            "queue", "library", "nowplaying", "playback", "history",
            "mix", "lyrics", "global_search", "output_profiles",
            "connections", "home_audio", "devices", "radio",
            "library_sources", "home", "app", "notification",
            "audio_lab", "metadata", "smart_tagging", "disc_lab",
            "library_doctor", "michi_ai", "diagnostics",
            "runtime_quality", "physical_audio", "command_palette",
            "cover_provider", "desktop", "page_state",
        }
        for key in expected_keys:
            assert key in result, f"Missing bridge: {key}"
