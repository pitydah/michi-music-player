"""Test that all BridgeFactory bridges are registered in QML_CONTEXT_BINDINGS."""
from unittest.mock import MagicMock

from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
from ui_qml_bridge.bridge_factory import BridgeFactory
from core.service_container import ServiceContainer

# Bridges registered as QML types (qmlRegisterType) are exempt from context binding
EXEMPT_QML_TYPES = {"cover"}

# Bridges registered conditionally (optional, not in canonical bindings)
EXEMPT_OPTIONAL = {"eq"}

# Providers or internal-only bridges
EXEMPT_INTERNAL = {"query_executor", "confirmation", "disc_lab"}


def _make_minimal_container() -> ServiceContainer:
    c = ServiceContainer()
    c.register("playback_service", MagicMock())
    c.register("worker_manager", MagicMock())
    c.register("database", MagicMock())
    c.register("settings_coordinator", MagicMock())
    c.register("settings_service", MagicMock())
    c.register("global_search_service", MagicMock())
    c.register("track_action_service", MagicMock())
    c.register("confirmation_service", MagicMock())
    c.register("notification_service", MagicMock())
    c.register("diagnostics_service", MagicMock())
    c.register("job_service", MagicMock())
    c.register("mix_query_service", MagicMock())
    c.register("playlist_service", MagicMock())
    c.register("queue_service", MagicMock())
    c.register("history_query_service", MagicMock())
    c.register("device_sync_service", MagicMock())
    c.register("home_audio_service", MagicMock())
    c.register("connection_service", MagicMock())
    c.register("radio_service", MagicMock())
    c.register("audio_lab_service", MagicMock())
    c.register("metadata_service", MagicMock())
    c.register("smart_tagging_service", MagicMock())
    c.register("library_doctor_service", MagicMock())
    c.register("library_sources_service", MagicMock())
    c.register("process_controller", MagicMock())
    return c


def test_all_factory_bridges_have_context_binding():
    container = _make_minimal_container()
    factory = BridgeFactory(container)
    factory.create_all()
    factory_bridge_keys = set(factory.bridges.keys())
    binding_values = set(QML_CONTEXT_BINDINGS.values())
    missing = factory_bridge_keys - binding_values - EXEMPT_QML_TYPES - EXEMPT_OPTIONAL - EXEMPT_INTERNAL
    assert not missing, f"Bridges missing from QML_CONTEXT_BINDINGS: {missing}"


def test_all_context_bindings_have_factory_bridge():
    container = _make_minimal_container()
    factory = BridgeFactory(container)
    factory.create_all()
    factory_bridge_keys = set(factory.bridges.keys())
    binding_values = set(QML_CONTEXT_BINDINGS.values())
    extra = binding_values - factory_bridge_keys - EXEMPT_QML_TYPES - EXEMPT_OPTIONAL - EXEMPT_INTERNAL
    assert not extra, f"QML_CONTEXT_BINDINGS references unknown bridges: {extra}"


def test_context_bindings_match_factory_bridges():
    container = _make_minimal_container()
    factory = BridgeFactory(container)
    factory.create_all()
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        if bridge_key in EXEMPT_QML_TYPES or bridge_key in EXEMPT_OPTIONAL or bridge_key in EXEMPT_INTERNAL:
            continue
        assert factory.has(bridge_key), (
            f"Bridge '{bridge_key}' (exposed as '{qml_name}') not created by factory"
        )
        assert factory.get(bridge_key) is not None, (
            f"Bridge '{bridge_key}' (exposed as '{qml_name}') is None"
        )
