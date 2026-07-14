"""Test that BridgeFactory is pure — no service creation, no _get_xxx methods.

All services are received pre-constructed from ServiceContainer/Bundle.
"""
from unittest.mock import MagicMock

from ui_qml_bridge.service_bundle import ServiceBundle
from ui_qml_bridge.bridge_factory import BridgeFactory


# ── Helpers ──

def _full_bundle() -> ServiceBundle:
    bundle = ServiceBundle()
    bundle.player_service = MagicMock()
    bundle.db = MagicMock()
    bundle.db_connection = MagicMock()
    bundle.search_engine = MagicMock()
    bundle.radio_manager = MagicMock()
    bundle.sync_manager = MagicMock()
    bundle.michi_link_controller = MagicMock()
    bundle.home_audio_controller = MagicMock()
    bundle.snapcast_controller = MagicMock()
    bundle.disc_service = MagicMock()
    bundle.worker_manager = MagicMock()
    bundle.metadata_service = MagicMock()
    bundle.smart_tagging_service = MagicMock()

    bundle.query_executor = MagicMock()
    bundle.library_query_service = MagicMock()
    bundle.track_action_service = MagicMock()
    bundle.playlist_service = MagicMock()
    bundle.settings_service = MagicMock()
    bundle.settings_coordinator = MagicMock()
    bundle.history_query_service = MagicMock()
    bundle.mix_query_service = MagicMock()
    bundle.library_sources_service = MagicMock()
    bundle.global_search_service = MagicMock()
    bundle.queue_service = MagicMock()
    bundle.job_service = MagicMock()
    bundle.action_registry = MagicMock()
    bundle.diagnostics_service = MagicMock()
    bundle.device_sync_service = MagicMock()
    bundle.audio_lab_service = MagicMock()
    bundle.event_bus = MagicMock()
    bundle.connection_factory = MagicMock()
    bundle.library_mutation_service = MagicMock()
    bundle.theme_service = MagicMock()
    bundle.accessibility_service = MagicMock()
    bundle.connection_service = MagicMock()
    bundle.home_audio_service = MagicMock()
    bundle.notification_service = MagicMock()
    return bundle


def _create_full_factory() -> BridgeFactory:
    bundle = _full_bundle()
    factory = BridgeFactory(bundle)
    factory.create_all()
    return factory


# ── Pure Factory Tests ──

def test_no_get_library_query_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_library_query_service')


def test_no_get_query_executor_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_query_executor')


def test_no_get_track_action_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_track_action_service')


def test_no_get_settings_runtime_coordinator_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_settings_runtime_coordinator')


def test_no_get_settings_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_settings_service')


def test_no_get_history_query_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_history_query_service')


def test_no_get_mix_query_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_mix_query_service')


def test_no_get_library_sources_service_method():
    factory = _create_full_factory()
    assert not hasattr(factory, '_get_library_sources_service')


def test_no_private_cache_attributes():
    factory = _create_full_factory()
    for attr in ('_qs_cache', '_qe_cache', '_tas_cache', '_ps_cache',
                 '_src_cache', '_lss_cache', '_gss_cache',
                 '_settings_service_cache', '_history_qs_cache', '_mix_qs_cache'):
        assert not hasattr(factory, attr), f"factory should not have {attr}"


def test_all_bridges_created():
    factory = _create_full_factory()
    expected = {
        "navigation", "action_registry", "job_bridge", "notification",
        "theme", "accessibility", "queue", "app", "library", "playback",
        "nowplaying", "mix", "lyrics", "connections", "home_audio",
        "devices", "radio", "selection_context", "playlists", "settings",
        "settings_v2", "eq", "audio_lab", "metadata", "smart_tagging",
        "disc_lab", "library_doctor", "michi_ai", "diagnostics",
        "runtime_quality", "physical_audio", "command_palette",
        "cover_provider", "desktop", "page_state", "history", "home",
        "output_profiles", "capability", "library_sources",
        "global_search", "route_registry", "app_state",
    }
    actual = set(factory.bridges.keys())
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"Missing bridges: {missing}"
    assert not extra, f"Unexpected bridges: {extra}"


def test_capabilities_registered():
    factory = _create_full_factory()
    caps = factory.capabilities
    assert "library" in caps
    assert caps["library"] is True


def test_create_all_returns_dict():
    factory = _create_full_factory()
    assert isinstance(factory.bridges, dict)


def test_get_and_has():
    factory = _create_full_factory()
    assert factory.has("navigation")
    assert factory.get("navigation") is not None
    assert not factory.has("nonexistent")
    assert factory.get("nonexistent") is None


def test_action_registry_is_shared():
    factory = _create_full_factory()
    ar1 = factory.get("action_registry")
    ar2 = factory._action_registry
    assert ar1 is ar2
    assert ar1 is not None


def test_settings_and_settings_v2_are_same():
    factory = _create_full_factory()
    s1 = factory.get("settings")
    s2 = factory.get("settings_v2")
    assert s1 is s2


def test_bind_action_handlers_does_not_raise():
    factory = _create_full_factory()
    factory.bind_action_handlers()


def test_repr():
    factory = _create_full_factory()
    r = repr(factory)
    assert "BridgeFactory" in r
    assert "bridges=" in r
