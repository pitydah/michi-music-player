"""Tests for topological composition: BridgeFactory + ServiceContainer integration."""

from unittest.mock import Mock

from core.service_container import ServiceRegistry
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle


def _make_container(**overrides) -> ServiceRegistry:
    c = ServiceRegistry()
    defaults = {
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
        "diagnostics_service": Mock(),
        "notification_service": Mock(),
        "action_registry": Mock(),
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
    def test_factory_accepts_container(self):
        c = _make_container()
        b = ServiceBundle()
        f = BridgeFactory(b, container=c)
        assert f.container is c

    def test_creates_navigation_bridge(self):
        f = BridgeFactory(_make_bundle(), container=_make_container())
        nav = f.create_navigation_bridge()
        assert nav is not None
        assert f.has("navigation")

    def test_creates_app_state_bridge(self):
        f = BridgeFactory(_make_bundle(), container=_make_container())
        br = f.create_app_state_bridge()
        assert br is not None

    def test_creates_theme_bridge_with_coordinator(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        theme = f.create_theme_bridge()
        assert theme is not None
        assert theme._coordinator is c.settings_coordinator

    def test_creates_accessibility_bridge_with_service(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        acc = f.create_accessibility_bridge()
        assert acc is not None
        assert acc._svc is c.settings_service

    def test_creates_notification_bridge_with_action_registry(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        f.create_job_bridge()
        f.get_action_registry()
        notif = f.create_notification_bridge()
        assert notif is not None
        assert notif._action_registry is c.action_registry

    def test_creates_michi_ai_with_diagnostics(self):
        c = _make_container()
        b = _make_bundle()
        f = BridgeFactory(b, container=c)
        f.create_navigation_bridge()
        f.create_job_bridge()
        f.get_action_registry()
        f.create_playlists_bridge()
        mi = f.create_michi_ai_bridge()
        assert mi is not None
        assert mi._diagnostics is c.diagnostics_service


class TestTopologicalOrder:
    def test_config_before_theme_bridge(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        f.create_theme_bridge()
        assert f.container.settings_coordinator is not None

    def test_playlist_service_before_track_action(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        assert f.container.playlist_service is not None
        assert f.container.track_action_service is not None

    def test_action_registry_before_notification(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        ar = f.get_action_registry()
        f.create_job_bridge()
        notif = f.create_notification_bridge()
        assert notif._action_registry is ar

    def test_worker_manager_before_job_bridge(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        f.create_job_bridge()
        assert c.worker_manager is not None

    def test_queue_service_available(self):
        c = _make_container()
        BridgeFactory(_make_bundle(), container=c)
        assert c.queue_service is not None


class TestAssertRequiredDependencies:
    def test_assert_passes_with_all_services(self):
        c = _make_container()
        b = _make_bundle()
        f = BridgeFactory(b, container=c)
        f.create_all()
        f.assert_required_dependencies()

    def test_assert_fails_when_diagnostics_none_in_michi(self):
        c = _make_container()
        c.register("diagnostics_service", None)
        b = _make_bundle()
        f = BridgeFactory(b, container=c)
        f.create_navigation_bridge()
        f.create_job_bridge()
        f.get_action_registry()
        f.create_playlists_bridge()
        f.create_michi_ai_bridge()
        import pytest
        with pytest.raises(AssertionError, match="must not be None"):
            f.assert_required_dependencies()

    def test_assert_fails_when_accessibility_no_service(self):
        c = _make_container()
        c.register("settings_service", None)
        c.register("settings_coordinator", None)
        b = _make_bundle()
        f = BridgeFactory(b, container=c)
        f.create_accessibility_bridge()
        import pytest
        with pytest.raises(AssertionError, match="must not be None"):
            f.assert_required_dependencies()


class TestCreateAll:
    def test_create_all_returns_dict(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_create_all_has_expected_bridges(self):
        c = _make_container()
        f = BridgeFactory(_make_bundle(), container=c)
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
