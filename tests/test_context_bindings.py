# -*- coding: utf-8 -*-
"""Tests for the canonical context_bindings mapping (Parche 4 supporting layer)."""
from ui_qml_bridge.context_bindings import (
    CONTEXT_BINDINGS,
    QML_CONTEXT_BINDINGS,
    _camel_to_snake,
    _EXPLICIT_BRIDGE_KEYS,
    ContextBinding,
)


class TestContextBindingsConsistency:
    def test_bindings_non_empty(self):
        assert len(CONTEXT_BINDINGS) > 30

    def test_every_binding_has_context_name_and_class(self):
        for binding in CONTEXT_BINDINGS:
            assert binding.context_name, f"missing context_name: {binding}"
            assert binding.bridge_class is not None

    def test_context_names_are_unique(self):
        names = [b.context_name for b in CONTEXT_BINDINGS]
        assert len(names) == len(set(names))

    def test_required_and_optional_services_are_tuples(self):
        for binding in CONTEXT_BINDINGS:
            assert isinstance(binding.required_services, tuple)
            assert isinstance(binding.optional_services, tuple)

    def test_required_services_are_non_empty_strings(self):
        for binding in CONTEXT_BINDINGS:
            for svc in binding.required_services:
                assert isinstance(svc, str) and svc, (
                    f"bad required service for {binding.context_name}: {svc!r}"
                )

    def test_lifecycle_owner_is_factory(self):
        for binding in CONTEXT_BINDINGS:
            assert binding.lifecycle_owner == "factory"

    def test_context_binding_is_dataclass_with_expected_fields(self):
        b = ContextBinding(bridge_class=object, context_name="x")
        assert b.required_services == ()
        assert b.optional_services == ()
        assert b.routes == ()
        assert b.lifecycle_owner == "factory"


class TestQmlContextBindings:
    def test_every_context_name_mapped(self):
        for binding in CONTEXT_BINDINGS:
            assert binding.context_name in QML_CONTEXT_BINDINGS

    def test_bridge_keys_are_non_empty_strings(self):
        for key in QML_CONTEXT_BINDINGS.values():
            assert isinstance(key, str) and key

    def test_bridge_keys_are_unique(self):
        keys = list(QML_CONTEXT_BINDINGS.values())
        assert len(keys) == len(set(keys)), "duplicate bridge keys"

    def test_qml_bindings_size_matches_context_bindings(self):
        assert len(QML_CONTEXT_BINDINGS) == len(CONTEXT_BINDINGS)

    def test_explicit_keys_resolved(self):
        for name, expected in _EXPLICIT_BRIDGE_KEYS.items():
            assert QML_CONTEXT_BINDINGS[name] == expected

    def test_known_key_derivations(self):
        assert QML_CONTEXT_BINDINGS["navigationBridge"] == "navigation"
        assert QML_CONTEXT_BINDINGS["appBridge"] == "app"
        assert QML_CONTEXT_BINDINGS["appStateBridge"] == "app_state"
        assert QML_CONTEXT_BINDINGS["globalSearchBridge"] == "global_search"
        assert QML_CONTEXT_BINDINGS["pageStateStore"] == "page_state"
        assert QML_CONTEXT_BINDINGS["actionRegistry"] == "action_registry"
        assert QML_CONTEXT_BINDINGS["jobBridge"] == "job_bridge"
        assert QML_CONTEXT_BINDINGS["confirmationBridge"] == "confirmation"


class TestCamelToSnake:
    def test_simple_word(self):
        assert _camel_to_snake("navigation") == "navigation"

    def test_camel_case(self):
        assert _camel_to_snake("appState") == "app_state"
        assert _camel_to_snake("globalSearch") == "global_search"
        assert _camel_to_snake("pageState") == "page_state"

    def test_leading_upper_not_prefixed(self):
        # leading uppercase char at i==0 is not prefixed with underscore
        assert _camel_to_snake("Home") == "home"
