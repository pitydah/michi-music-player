"""Test that all BridgeFactory bridges are registered in QML_CONTEXT_BINDINGS."""
from unittest.mock import MagicMock

from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.service_bundle import ServiceBundle

# Bridges registered as QML types (qmlRegisterType) are exempt from context binding
EXEMPT_QML_TYPES = {"cover"}

# Bridges registered conditionally (optional, not in canonical bindings)
EXEMPT_OPTIONAL = {"eq"}

# Providers or internal-only bridges
EXEMPT_INTERNAL = set()


def _make_minimal_bundle() -> ServiceBundle:
    bundle = ServiceBundle()
    bundle.worker_manager = MagicMock()
    return bundle


def test_all_factory_bridges_have_context_binding():
    bundle = _make_minimal_bundle()
    factory = BridgeFactory(bundle)
    factory.create_all()
    factory_bridge_keys = set(factory.bridges.keys())
    binding_values = set(QML_CONTEXT_BINDINGS.values())
    missing = factory_bridge_keys - binding_values - EXEMPT_QML_TYPES - EXEMPT_OPTIONAL - EXEMPT_INTERNAL
    assert not missing, f"Bridges missing from QML_CONTEXT_BINDINGS: {missing}"


def test_all_context_bindings_have_factory_bridge():
    bundle = _make_minimal_bundle()
    factory = BridgeFactory(bundle)
    factory.create_all()
    factory_bridge_keys = set(factory.bridges.keys())
    binding_values = set(QML_CONTEXT_BINDINGS.values())
    extra = binding_values - factory_bridge_keys - EXEMPT_QML_TYPES - EXEMPT_OPTIONAL - EXEMPT_INTERNAL
    assert not extra, f"QML_CONTEXT_BINDINGS references unknown bridges: {extra}"


def test_context_bindings_match_factory_bridges():
    bundle = _make_minimal_bundle()
    factory = BridgeFactory(bundle)
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
