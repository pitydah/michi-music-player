"""Tests for the public BridgeFactory contract."""

from pathlib import Path
from unittest.mock import MagicMock

from core.service_container import ServiceContainer
from ui_qml_bridge.bridge_factory import BridgeFactory, create_all_bridges


BRIDGE_FACTORY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "ui_qml_bridge"
    / "bridge_factory.py"
)
SERVICE_BUNDLE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "ui_qml_bridge"
    / "service_bundle.py"
)


def _make_container(**overrides) -> ServiceContainer:
    container = ServiceContainer()
    services = {
        "action_registry": MagicMock(),
        "audio_lab_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "connection_factory": MagicMock(),
        "connection_service": MagicMock(),
        "database": MagicMock(),
        "device_sync_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "disc_lab_service": MagicMock(),
        "folder_service": MagicMock(),
        "global_search_service": MagicMock(),
        "history_query_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "job_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "library_mutation_service": MagicMock(),
        "library_query_service": MagicMock(),
        "library_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "lyrics_service": MagicMock(),
        "metadata_service": MagicMock(),
        "michi_ai_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "mix_service": MagicMock(),
        "mobile_sync_service": MagicMock(),
        "navigation_service": MagicMock(),
        "notification_service": MagicMock(),
        "playback_service": MagicMock(),
        "playlist_service": MagicMock(),
        "process_controller": MagicMock(),
        "query_executor": MagicMock(),
        "queue_service": MagicMock(),
        "radio_service": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "track_action_service": MagicMock(),
        "worker_manager": MagicMock(),
    }
    services.update(overrides)
    for name, service in services.items():
        container.register(name, service)
    return container


class TestBridgeFactoryAcceptsServiceContainer:
    def test_accepts_service_container(self):
        container = _make_container()

        factory = BridgeFactory(container)

        assert factory._container is container

    def test_accepts_container_from_bootstrap(self):
        from core.application_bootstrap import ApplicationBootstrap

        bootstrap = ApplicationBootstrap()

        factory = BridgeFactory(bootstrap.container)

        assert factory._container is bootstrap.container


class TestNoServiceBundleImports:
    def test_no_service_bundle_import(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        assert "service_bundle" not in content

    def test_no_get_cache_patterns(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        forbidden = [
            "_get_query_executor",
            "_get_track_action_service",
            "_get_playlist_service",
            "_get_settings_service",
            "_service_cache",
            "_query_executor_cache",
            "_settings_cache",
            "_playlist_cache",
            "_get_action_registry",
        ]

        violations = [pattern for pattern in forbidden if pattern in content]

        assert violations == []

    def test_service_bundle_is_legacy_only(self):
        content = SERVICE_BUNDLE_PATH.read_text()
        assert "LEGACY_ONLY" in content


class TestContainerAccess:
    def test_container_provides_required_services(self):
        container = _make_container()

        for name in (
            "playback_service",
            "connection_factory",
            "worker_manager",
            "settings_service",
            "queue_service",
            "action_registry",
        ):
            assert container.contains(name)

    def test_missing_services_detected(self):
        missing = BridgeFactory(ServiceContainer()).validate_required_dependencies()

        assert "playback_service" in missing
        assert "connection_factory" in missing
        assert "action_registry" in missing

    def test_validate_required_dependencies_all_present(self):
        missing = BridgeFactory(_make_container()).validate_required_dependencies()

        assert missing == []


class TestBridgeLifecycle:
    def test_create_all_returns_key_bridges(self):
        result = BridgeFactory(_make_container()).create_all()

        assert isinstance(result, dict)
        for name in (
            "page_state",
            "navigation",
            "action_registry",
            "library",
            "playback",
            "nowplaying",
            "queue",
            "settings",
            "notification",
            "home",
            "app",
        ):
            assert name in result

    def test_bridges_property_returns_copy(self):
        factory = BridgeFactory(_make_container())
        factory.create_all()

        bridges = factory.bridges
        bridges["fake"] = MagicMock()

        assert "fake" not in factory.bridges

    def test_capabilities_property_returns_copy(self):
        factory = BridgeFactory(_make_container())
        factory._capabilities["test"] = True

        capabilities = factory.capabilities
        capabilities["other"] = False

        assert "other" not in factory.capabilities


class TestIndividualBridges:
    def test_public_create_methods_register_bridges(self):
        factory = BridgeFactory(_make_container())

        factory.create_page_state_store()
        factory.create_navigation_bridge()
        factory.create_action_registry_bridge()
        factory.create_job_bridge()
        factory.create_library_bridge()
        factory.create_playback_bridge()
        factory.create_queue_bridge()

        assert {
            "page_state",
            "navigation",
            "action_registry",
            "job_bridge",
            "library",
            "nowplaying",
            "playback",
            "queue",
        } <= factory.bridges.keys()

    def test_create_notification_after_dependencies(self):
        factory = BridgeFactory(_make_container())
        factory.create_action_registry_bridge()
        factory.create_job_bridge()

        factory.create_notification_bridge()

        assert factory.has("notification")


class TestSettingsIdentity:
    def test_create_settings_bridge_uses_shared_identity(self):
        factory = BridgeFactory(_make_container())

        factory.create_settings_bridge()

        assert factory.get("settings") is factory.get("settings_v2")

    def test_create_all_uses_shared_settings_identity(self):
        result = BridgeFactory(_make_container()).create_all()

        assert result["settings"] is result["settings_v2"]


class TestEdgeCases:
    def test_create_all_is_idempotent(self):
        factory = BridgeFactory(_make_container())

        first = factory.create_all()
        second = factory.create_all()

        assert first is second

    def test_independent_bridge_can_use_empty_container(self):
        factory = BridgeFactory(ServiceContainer())

        factory.create_page_state_store()

        assert factory.has("page_state")

    def test_bind_action_handlers_no_crash_without_registry(self):
        factory = BridgeFactory(_make_container())

        factory.bind_action_handlers()

        assert factory.bridges == {}


class TestCreateAllBridgesFunction:
    def test_create_all_bridges_function(self):
        result = create_all_bridges(_make_container())

        assert "navigation" in result
        assert "action_registry" in result

    def test_create_all_bridges_no_service_bundle_import(self):
        content = BRIDGE_FACTORY_PATH.read_text()
        assert "ServiceBundle" not in content
