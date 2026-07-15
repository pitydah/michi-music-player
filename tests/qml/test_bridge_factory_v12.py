"""Tests for BridgeFactory v12 — ServiceContainer, deterministic order, no ServiceBundle."""
from unittest.mock import MagicMock
from pathlib import Path


from ui_qml_bridge.bridge_factory import BridgeFactory, INFRASTRUCTURE, DOMAIN, AGGREGATORS
from core.service_container import ServiceContainer


BRIDGE_FACTORY_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "bridge_factory.py"
SERVICE_BUNDLE_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "service_bundle.py"


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


class TestBridgeFactoryAcceptsServiceContainer:
    def test_accepts_service_container(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f._container is c

    def test_accepts_container_from_bootstrap(self):
        from core.application_bootstrap import ApplicationBootstrap
        bootstrap = ApplicationBootstrap()
        f = BridgeFactory(bootstrap.container)
        assert f._container is bootstrap.container


class TestNoServiceBundleImports:
    def test_no_service_bundle_import(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        assert "service_bundle" not in content, "bridge_factory still imports service_bundle"

    def test_no_get_cache_patterns(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        forbidden = [
            "_get_query_executor", "_get_track_action_service",
            "_get_playlist_service", "_get_settings_service",
            "_service_cache", "_query_executor_cache",
            "_settings_cache", "_playlist_cache",
            "_get_action_registry",
        ]
        violations = [f for f in forbidden if f in content]
        assert len(violations) == 0, f"Found forbidden patterns: {violations}"

    def test_service_bundle_is_legacy_only(self):
        content = SERVICE_BUNDLE_PATH.read_text()
        assert "LEGACY_ONLY" in content, "service_bundle.py should be marked LEGACY_ONLY"


class TestContainerAccess:
    def test_container_provides_services(self):
        c = _make_container()
        assert c.contains("playback_service")
        assert c.contains("worker_manager")
        assert c.contains("database")

    def test_missing_service_detected(self):
        c = ServiceContainer()
        f = BridgeFactory(c)
        missing = f.validate_required_dependencies()
        assert "playback_service" in missing
        assert "worker_manager" in missing

    def test_validate_required_dependencies_all_present(self):
        c = _make_container()
        f = BridgeFactory(c)
        missing = f.validate_required_dependencies()
        assert missing == []


class TestBridgeLifecycle:
    def test_create_all_returns_dict(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert isinstance(result, dict)

    def test_create_all_contains_infrastructure(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        for name in INFRASTRUCTURE:
            key = {"page_state": "page_state", "route_registry": "route_registry",
                   "navigation": "navigation", "action_registry": "action_registry",
                   "query_executor": "query_executor", "job_bridge": "job_bridge",
                   "confirmation": "confirmation", "theme": "theme",
                   "accessibility": "accessibility"}.get(name, name)
            assert key in result, f"Missing infrastructure bridge: {key}"

    def test_create_all_contains_domain_bridges(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        for name in DOMAIN:
            key = {"library_sources": "library_sources", "library": "library",
                   "nowplaying": "nowplaying"}.get(name, name)
            assert key in result, f"Missing domain bridge: {key}"

    def test_create_all_contains_aggregators(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        for name in AGGREGATORS:
            assert name in result, f"Missing aggregator bridge: {name}"

    def test_bridges_property_returns_copy(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_all()
        bridges = f.bridges
        bridges["fake"] = MagicMock()
        assert "fake" not in f._bridges

    def test_capabilities_property_returns_copy(self):
        c = _make_container()
        f = BridgeFactory(c)
        f._capabilities["test"] = True
        caps = f.capabilities
        caps["other"] = False
        assert "other" not in f._capabilities


class TestIndividualBridges:
    def test_create_navigation(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_navigation_bridge()
        assert f.has("navigation")

    def test_create_page_state(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_page_state_store()
        assert f.has("page_state")

    def test_create_action_registry(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_action_registry_bridge()
        assert f.has("action_registry")

    def test_create_job_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_job_bridge()
        assert f.has("job_bridge")

    def test_create_library_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_library_bridge()
        assert f.has("library")

    def test_create_playback_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_playback_bridge()
        assert f.has("playback")
        assert f.has("nowplaying")

    def test_create_queue_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_queue_bridge()
        assert f.has("queue")

    def test_create_notification_after_action_registry_and_job(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_action_registry_bridge()
        f.create_job_bridge()
        f.create_notification_bridge()
        assert f.has("notification")

    def test_create_capability_bridge(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_capability_bridge()
        assert f.has("capability")

    def test_create_all_bridges(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert len(result) >= 5


class TestDeterministicOrder:
    def test_create_follows_infrastructure_first(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_all()
        order = list(f._bridges.keys())
        infra_keys = [k for k in INFRASTRUCTURE]
        expected_infra = {
            "page_state": "page_state", "route_registry": "route_registry",
            "navigation": "navigation", "action_registry": "action_registry",
            "query_executor": "query_executor", "job_bridge": "job_bridge",
            "confirmation": "confirmation", "theme": "theme", "accessibility": "accessibility",
        }
        for k in infra_keys:
            ek = expected_infra.get(k, k)
            assert ek in order, f"{ek} not in creation order"

    def test_create_follows_domain_after_infrastructure(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_all()
        order = list(f._bridges.keys())
        infra_end = max(order.index(k) for k in ("accessibility", "theme", "confirmation", "job_bridge",
                                                 "query_executor", "action_registry", "navigation",
                                                 "route_registry", "page_state") if k in order)
        domain_keys = ["library_sources", "library", "playback", "queue"]
        for dk in domain_keys:
            if dk in order:
                assert order.index(dk) > infra_end, f"{dk} before infrastructure finished"

    def test_get_returns_none_for_missing(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.get("nonexistent") is None

    def test_has_returns_false_for_missing(self):
        c = _make_container()
        f = BridgeFactory(c)
        assert f.has("nonexistent") is False


class TestSettingsIdentity:
    def test_settings_identity(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.create_settings_bridge()
        assert f._bridges["settings"] is f._bridges["settings_v2"]

    def test_create_all_creates_shared_settings(self):
        c = _make_container()
        f = BridgeFactory(c)
        result = f.create_all()
        assert result["settings"] is result["settings_v2"]


class TestEdgeCases:
    def test_create_twice_returns_same_dict_ref(self):
        c = _make_container()
        f = BridgeFactory(c)
        r1 = f.create_all()
        r2 = f.create_all()
        assert r1 is r2

    def test_empty_container_does_not_crash(self):
        c = ServiceContainer()
        f = BridgeFactory(c)
        f.create_navigation_bridge()
        assert f.has("navigation")

    def test_bind_action_handlers_no_crash_without_registry(self):
        c = _make_container()
        f = BridgeFactory(c)
        f.bind_action_handlers()
        assert True

    def test_validate_required_dependencies_empty_container(self):
        c = ServiceContainer()
        f = BridgeFactory(c)
        missing = f.validate_required_dependencies()
        assert "playback_service" in missing


class TestCreateAllBridgesFunction:
    def test_create_all_bridges_function(self):
        c = _make_container()
        from ui_qml_bridge.bridge_factory import create_all_bridges
        result = create_all_bridges(c)
        assert isinstance(result, dict)
        assert "navigation" in result
        assert "action_registry" in result

    def test_create_all_bridges_no_service_bundle_import(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        assert "ServiceBundle" not in content
