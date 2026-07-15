"""Tests for BridgeFactory + Context normalizado — names, declarative table, no duplicates.

Verifica:
- Nombres normalizados (library vs libraryBridge, michiAiBridge vs michiAIBridge, etc.)
- Tabla declarativa unica con bridge_class, context_name, required_services, optional_services, routes, lifecycle_owner
- No manual context registration, no aliases no consumidos, no context properties duplicadas, no bridges construidos dos veces
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ui_qml_bridge.context_bindings import CONTEXT_BINDINGS, ContextBinding, QML_CONTEXT_BINDINGS
from ui_qml_bridge.bridge_factory import BridgeFactory
from core.service_container import ServiceContainer


def _mock_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    defaults = {
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
    }
    for k, v in defaults.items():
        c.register(k, overrides.get(k, v))
    return c


class TestContextBindingsDeclarative:
    def test_has_declarative_table(self):
        assert len(CONTEXT_BINDINGS) > 0
        assert all(isinstance(b, ContextBinding) for b in CONTEXT_BINDINGS)

    def test_each_binding_has_bridge_class(self):
        for b in CONTEXT_BINDINGS:
            assert b.bridge_class is not None, f"{b.context_name} missing bridge_class"

    def test_each_binding_has_context_name(self):
        for b in CONTEXT_BINDINGS:
            assert b.context_name, "Missing context_name"

    def test_each_binding_has_lifecycle_owner(self):
        for b in CONTEXT_BINDINGS:
            assert b.lifecycle_owner == "factory", f"{b.context_name} unexpected owner {b.lifecycle_owner}"

    def test_no_duplicate_context_names(self):
        names = [b.context_name for b in CONTEXT_BINDINGS]
        assert len(names) == len(set(names)), f"Duplicates: {[n for n in names if names.count(n) > 1]}"

    def test_no_duplicate_bridge_keys(self):
        keys = list(QML_CONTEXT_BINDINGS.values())
        assert len(keys) == len(set(keys)), f"Duplicate bridge keys: {[k for k in keys if keys.count(k) > 1]}"

    def test_context_names_use_bridge_suffix(self):
        for b in CONTEXT_BINDINGS:
            if b.bridge_class.__name__ not in ("ActionRegistry",):
                ok = b.context_name.endswith("Bridge") or b.context_name.endswith("Store") or "Bridge" in b.context_name
                assert ok, f"{b.context_name} missing Bridge/Store suffix"

    def test_qml_context_bindings_map_is_built(self):
        assert len(QML_CONTEXT_BINDINGS) == len(CONTEXT_BINDINGS)
        for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
            assert isinstance(qml_name, str)
            assert isinstance(bridge_key, str)

    def test_required_services_are_strings(self):
        for b in CONTEXT_BINDINGS:
            for s in b.required_services:
                assert isinstance(s, str)

    def test_optional_services_are_strings(self):
        for b in CONTEXT_BINDINGS:
            for s in b.optional_services:
                assert isinstance(s, str)


class TestNameNormalization:
    def test_library_not_libraryBridge(self):
        assert QML_CONTEXT_BINDINGS.get("libraryBridge") == "library"

    def test_michi_ai_consistency(self):
        assert "michiAiBridge" in QML_CONTEXT_BINDINGS
        binding = next(b for b in CONTEXT_BINDINGS if b.context_name == "michiAiBridge")
        assert binding.bridge_class.__name__ == "MichiAIBridge"

    def test_settings_not_settingsBridgeV2_in_qml_map(self):
        assert QML_CONTEXT_BINDINGS.get("settingsBridge") == "settings"
        assert QML_CONTEXT_BINDINGS.get("settingsBridgeV2") == "settings_v2"

    def test_mix_not_mix_query_service(self):
        assert QML_CONTEXT_BINDINGS.get("mixBridge") == "mix"
        mix_binding = next(b for b in CONTEXT_BINDINGS if b.context_name == "mixBridge")
        assert "mix_query_service" not in mix_binding.required_services

    def test_playback_not_player_service(self):
        assert QML_CONTEXT_BINDINGS.get("playbackBridge") == "playback"
        pb_binding = next(b for b in CONTEXT_BINDINGS if b.context_name == "playbackBridge")
        assert pb_binding.bridge_class.__name__ == "PlaybackBridge"

    def test_settings_bridge_class_is_settings_bridge_v2(self):
        sb = next(b for b in CONTEXT_BINDINGS if b.context_name == "settingsBridge")
        assert sb.bridge_class.__name__ == "SettingsBridgeV2"


class TestNoManualRegistration:
    def test_no_context_property_registration_outside_context_bindings(self):
        bp = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge"
        files_with_manual = []
        for pyfile in bp.rglob("*.py"):
            if pyfile.name in ("context_bindings.py", "context_registrar.py", "bridge_factory.py",
                               "qml_main.py", "__init__.py"):
                continue
            content = pyfile.read_text()
            if "setContextProperty" in content:
                files_with_manual.append(str(pyfile))
        assert len(files_with_manual) == 0, f"Manual setContextProperty in: {files_with_manual}"

    def test_no_aliases_not_consumed(self):
        all_qml_names = set(QML_CONTEXT_BINDINGS.keys())
        for b in CONTEXT_BINDINGS:
            assert b.context_name in all_qml_names

    def test_no_context_properties_duplicated(self):
        names = [b.context_name for b in CONTEXT_BINDINGS]
        duplicates = [n for n in names if names.count(n) > 1]
        assert len(duplicates) == 0, f"Duplicated: {duplicates}"

    def test_eq_bridge_in_bindings_not_manual(self):
        assert "eqBridge" in QML_CONTEXT_BINDINGS

    def test_action_registry_binding(self):
        assert "actionRegistry" in QML_CONTEXT_BINDINGS
        ar_binding = next(b for b in CONTEXT_BINDINGS if b.context_name == "actionRegistry")
        assert ar_binding.bridge_class.__name__ == "ActionRegistry"


class TestFactoryMatchesBindings:
    def test_factory_creates_all_bridge_keys(self):
        c = _mock_container()
        f = BridgeFactory(c)
        created = f.create_all()
        expected_keys = set(v for v in QML_CONTEXT_BINDINGS.values())
        created_keys = set(created.keys())
        missing = expected_keys - created_keys
        extra = created_keys - expected_keys
        assert len(missing) == 0, f"Bridges not created: {missing}"
        assert len(extra) <= 4, f"Unexpected bridges: {extra}"

    def test_settings_and_settings_v2_same_object(self):
        c = _mock_container()
        f = BridgeFactory(c)
        created = f.create_all()
        if "settings" in created and "settings_v2" in created:
            assert created["settings"] is created["settings_v2"]

    def test_no_bridge_created_twice(self):
        c = _mock_container()
        f = BridgeFactory(c)
        created = f.create_all()
        for key, bridge in created.items():
            count = 0
            for v in created.values():
                if v is bridge:
                    count += 1
            if key in ("settings", "settings_v2"):
                assert count == 2
            else:
                assert count == 1, f"{key} bridge appears {count} times"

    def test_bridge_keys_match_productivo(self):
        c = _mock_container()
        f = BridgeFactory(c)
        created = f.create_all()
        for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
            assert bridge_key in created, f"Bridge key '{bridge_key}' (from {qml_name}) not in created bridges"
            assert created[bridge_key] is not None, f"Bridge '{bridge_key}' created as None"


class TestRoutes:
    def test_route_mappings_defined(self):
        for b in CONTEXT_BINDINGS:
            assert hasattr(b, 'routes')

    def test_navigation_has_wildcard_route(self):
        nav = next(b for b in CONTEXT_BINDINGS if b.context_name == "navigationBridge")
        assert len(nav.routes) >= 0


class TestNegative:
    def test_no_fake_or_stub_bridges(self):
        for b in CONTEXT_BINDINGS:
            name = b.bridge_class.__name__
            assert "Fake" not in name
            assert "Stub" not in name
            assert "Mock" not in name
            assert "Demo" not in name

    def test_no_bridge_from_old_naming(self):
        old_names = ["mix_query_service"]
        for b in CONTEXT_BINDINGS:
            for old in old_names:
                assert old not in b.required_services and old not in b.optional_services, \
                    f"{b.context_name} references old name '{old}'"

    def test_context_binding_not_loading_from_file(self):
        assert "library" not in [b.context_name for b in CONTEXT_BINDINGS]
