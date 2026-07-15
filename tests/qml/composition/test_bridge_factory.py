"""Tests for BridgeFactory — thin bridge creation, no caching, validate dependencies."""
from unittest.mock import Mock

from ui_qml_bridge.bridge_factory import BridgeFactory
from core.service_container import ServiceContainer
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    for k, v in {
        "playback_service": Mock(),
        "worker_manager": Mock(),
        "database": Mock(),
        "settings_coordinator": Mock(),
        "settings_service": Mock(),
        "global_search_service": Mock(),
        "track_action_service": Mock(),
        "confirmation_service": Mock(),
        "notification_service": Mock(),
        "diagnostics_service": Mock(),
        "job_service": Mock(),
        "mix_query_service": Mock(),
        "playlist_service": Mock(),
        "queue_service": Mock(),
        "history_query_service": Mock(),
        "device_sync_service": Mock(),
        "home_audio_service": Mock(),
        "connection_service": Mock(),
        "radio_service": Mock(),
        "audio_lab_service": Mock(),
        "metadata_service": Mock(),
        "smart_tagging_service": Mock(),
        "library_doctor_service": Mock(),
        "library_sources_service": Mock(),
        "process_controller": Mock(),
    }.items():
        c.register(k, overrides.get(k, v))
    return c


class TestBridgeFactoryCreation:
    def test_creates_empty_bridges(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.bridges == {}

    def test_has_returns_false_for_uncreated(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.has("navigation") is False

    def test_get_returns_none_for_uncreated(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.get("navigation") is None

    def test_validate_no_missing_deps(self):
        c = _make_container()
        f = BridgeFactory(c)
        missing = f.validate_required_dependencies()
        assert missing == []

    def test_validate_detects_missing_deps(self):
        c = ServiceContainer()
        f = BridgeFactory(c)
        missing = f.validate_required_dependencies()
        assert "playback_service" in missing
        assert "worker_manager" in missing


class TestBridgeFactoryCreate:
    def test_create_navigation_bridge(self):
        f = BridgeFactory(_make_container())
        f.create_navigation_bridge()
        assert f.has("navigation")
        assert f.get("navigation") is not None

    def test_create_navigation_bridge_idempotent(self):
        f = BridgeFactory(_make_container())
        f.create_navigation_bridge()
        nav1 = f.get("navigation")
        f.create_navigation_bridge()
        nav2 = f.get("navigation")
        assert nav1 is nav2

    def test_create_app_state_bridge(self):
        f = BridgeFactory(_make_container())
        f.create_app_state_bridge()
        assert f.has("app_state")

    def test_create_theme_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_theme_bridge()
        assert f.has("theme")

    def test_create_notification_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("notification")

    def test_create_all_returns_dict(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_create_all_has_expected_bridges(self):
        f = BridgeFactory(_make_container())
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


class TestBridgeFactoryIntegration:
    def test_create_all_with_missing_deps_does_not_crash(self):
        c = ServiceContainer()
        c.register("worker_manager", Mock())
        f = BridgeFactory(c)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_no_bridge_is_none_capability(self):
        f = BridgeFactory(_make_container())
        result = f.create_all()
        assert "capability" in result
