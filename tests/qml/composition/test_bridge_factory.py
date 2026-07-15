"""Tests for BridgeFactory — thin bridge creation, no caching, validate dependencies."""
from unittest.mock import Mock

from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


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
        "settings_coordinator": Mock(),
        "job_service": Mock(),
    }.items():
        setattr(b, k, overrides.get(k, v))
    return b


class TestBridgeFactoryCreation:
    def test_creates_empty_bridges(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        assert f.bridges == {}

    def test_has_returns_false_for_uncreated(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        assert f.has("navigation") is False

    def test_get_returns_none_for_uncreated(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        assert f.get("navigation") is None

    def test_validate_no_missing_deps(self):
        b = _make_bundle()
        f = BridgeFactory(b)
        missing = f.validate_required_dependencies()
        assert missing == []

    def test_validate_detects_missing_deps(self):
        b = _make_bundle()
        b.worker_manager = None
        f = BridgeFactory(b)
        missing = f.validate_required_dependencies()
        assert "worker_manager" in missing


class TestBridgeFactoryCreate:
    def test_create_navigation_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_navigation_bridge()
        assert f.has("navigation")
        assert f.get("navigation") is not None

    def test_create_navigation_bridge_idempotent(self):
        f = BridgeFactory(_make_bundle())
        f.create_navigation_bridge()
        nav1 = f.get("navigation")
        f.create_navigation_bridge()
        nav2 = f.get("navigation")
        assert nav1 is nav2

    def test_create_app_state_bridge(self):
        f = BridgeFactory(_make_bundle())
        f.create_app_state_bridge()
        assert f.has("app_state")

    def test_create_theme_bridge(self):
        b = _make_bundle()
        b.settings_coordinator = Mock()
        f = BridgeFactory(b)
        f.create_theme_bridge()
        assert f.has("theme")

    def test_create_notification_bridge(self):
        b = _make_bundle()
        b.worker_manager = Mock()
        f = BridgeFactory(b)
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("notification")

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


class TestBridgeFactoryIntegration:
    def test_create_all_with_missing_deps_does_not_crash(self):
        b = ServiceBundle()
        b.worker_manager = Mock()
        f = BridgeFactory(b)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_no_bridge_is_none_capability(self):
        f = BridgeFactory(_make_bundle())
        result = f.create_all()
        assert "capability" in result
