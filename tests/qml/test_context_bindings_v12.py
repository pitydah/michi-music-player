"""Test context bindings canonical naming, contract enforcement.

Tests:
- Canonical container names: database, playback_service, global_search_service,
  device_sync_service, connection_service, home_audio_service, radio_service
- ContextBinding has route_id contract
- REQUIRED service absent -> ContractViolation
- OPTIONAL service absent -> capability false (no error)
- No None registered as context
- No duplicate instances of same service
"""
import pytest
from unittest.mock import MagicMock

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine

from ui_qml_bridge.context_bindings import CONTEXT_BINDINGS, ContextBinding
from ui_qml_bridge.context_registrar import ContextRegistrar, ContractViolation, CANONICAL_MAP


CANONICAL_RULES = {
    "db": "database",
    "player_service": "playback_service",
    "search_engine": "global_search_service",
    "sync_manager": "device_sync_service",
    "michi_link_controller": "connection_service",
    "home_audio_controller": "home_audio_service",
    "radio_manager": "radio_service",
}


class _FakeBridge(QObject):
    pass


class _OtherBridge(QObject):
    pass


@pytest.fixture
def engine():
    eng = MagicMock(spec=QQmlApplicationEngine)
    rc = MagicMock()
    eng.rootContext.return_value = rc
    return eng


@pytest.fixture
def registrar(engine):
    return ContextRegistrar(engine)


_CONTAINER_SERVICES = {
    "database", "playback_service", "worker_manager", "global_search_service",
    "device_sync_service", "connection_service", "home_audio_service",
    "radio_service", "settings_service", "library_sources_service",
    "library_query_service", "history_query_service", "metadata_service",
    "job_service", "audio_lab_service", "smart_tagging_service",
    "notification_service", "diagnostics_service", "confirmation_service",
    "track_action_service", "playlist_service", "queue_service",
    "mix_query_service", "mix_service", "runtime_persistence",
    "theme_service", "accessibility_service", "action_registry",
    "process_controller",
}
_CONTAINER_STORE: dict[str, object] = {}


@pytest.fixture
def fake_container():
    _CONTAINER_STORE.clear()
    c = MagicMock()
    for s in _CONTAINER_SERVICES:
        _CONTAINER_STORE[s] = _FakeBridge()
    def get(name):
        return _CONTAINER_STORE.get(name)
    def contains(name):
        return name in _CONTAINER_STORE
    c.get = get
    c.contains = contains
    return c


# ── Canonical naming ──

class TestCanonicalNames:
    def test_canonical_map_contains_all_renamed(self):
        for old, canonical in CANONICAL_RULES.items():
            assert CANONICAL_MAP.get(old) == canonical, (
                f"Missing canonical mapping: {old} -> {canonical}"
            )

    def test_required_services_use_canonical_names(self):
        violations = []
        for binding in CONTEXT_BINDINGS:
            for svc in binding.required_services:
                if svc in CANONICAL_RULES:
                    violations.append(
                        f"{binding.context_name} uses '{svc}' instead of "
                        f"canonical '{CANONICAL_RULES[svc]}'"
                    )
            for svc in binding.optional_services:
                if svc in CANONICAL_RULES:
                    violations.append(
                        f"{binding.context_name} uses '{svc}' instead of "
                        f"canonical '{CANONICAL_RULES[svc]}'"
                    )
        if violations:
            pytest.fail("\n".join(violations))

    def test_no_non_canonical_names_in_bindings(self):
        non_canonical = {"db", "player_service", "search_engine",
                         "sync_manager", "michi_link_controller",
                         "home_audio_controller", "radio_manager"}
        for binding in CONTEXT_BINDINGS:
            for svc in binding.required_services:
                assert svc not in non_canonical, (
                    f"{binding.context_name}: '{svc}' is non-canonical"
                )
            for svc in binding.optional_services:
                assert svc not in non_canonical, (
                    f"{binding.context_name}: '{svc}' is non-canonical"
                )


# ── Route contract ──

class TestRouteContract:
    def test_context_binding_has_route_id(self):
        for binding in CONTEXT_BINDINGS:
            assert hasattr(binding, 'route_id'), (
                f"{binding.context_name} missing route_id"
            )

    def test_route_id_is_string(self):
        for binding in CONTEXT_BINDINGS:
            assert isinstance(binding.route_id, str), (
                f"{binding.context_name}.route_id must be str, got {type(binding.route_id)}"
            )


# ── REQUIRED absent ──

class TestRequiredAbsent:
    def test_required_absent_raises(self, registrar, fake_container):
        strict = ContextBinding(_FakeBridge, "strictBridge",
                                required_services=("nonexistent_service",))
        with pytest.raises(ContractViolation):
            registrar.register_with_contract(strict, _FakeBridge(), fake_container)

    def test_required_present_ok(self, registrar, fake_container):
        strict = ContextBinding(_FakeBridge, "okBridge",
                                required_services=("database",))
        registrar.register_with_contract(strict, _FakeBridge(), fake_container)
        assert "okBridge" in registrar.names

    def test_multiple_required_absent_fails(self, registrar, fake_container):
        strict = ContextBinding(_FakeBridge, "multiBridge",
                                required_services=("database", "nonexistent_a", "nonexistent_b"))
        with pytest.raises(ContractViolation):
            registrar.register_with_contract(strict, _FakeBridge(), fake_container)

    def test_empty_required_ok(self, registrar, fake_container):
        strict = ContextBinding(_FakeBridge, "noReqBridge")
        registrar.register_with_contract(strict, _FakeBridge(), fake_container)
        assert "noReqBridge" in registrar.names


# ── OPTIONAL absent ──

class TestOptionalAbsent:
    def test_optional_absent_does_not_raise(self, registrar, fake_container):
        binding = ContextBinding(_FakeBridge, "optBridge",
                                 optional_services=("nonexistent_opt",))
        try:
            registrar.register_with_contract(binding, _FakeBridge(), fake_container)
        except ContractViolation:
            pytest.fail("OPTIONAL absent should not raise ContractViolation")

    def test_optional_present_ok(self, registrar, fake_container):
        binding = ContextBinding(_FakeBridge, "optPresent",
                                 optional_services=("database",))
        registrar.register_with_contract(binding, _FakeBridge(), fake_container)
        assert "optPresent" in registrar.names


# ── No None context ──

class TestNoNoneContext:
    def test_register_none_skipped(self, registrar, engine):
        registrar.register("nullBridge", None)
        assert registrar.count == 0

    def test_register_none_adds_violation(self, registrar, engine):
        registrar.register("nullBridge", None)
        assert len(registrar.violations) >= 1
        assert any("None" in v for v in registrar.violations)

    def test_none_in_dict_skipped(self, registrar, engine):
        registrar.register_dict({"bridgeA": _FakeBridge(), "nullBridge": None})
        assert registrar.count == 1


# ── No duplicate instances ──

class TestNoDuplicateService:
    def test_duplicate_same_type_allowed(self, registrar, engine):
        b1 = _FakeBridge()
        b2 = _FakeBridge()
        registrar.register("dup", b1)
        registrar.register("dup", b2)
        assert registrar.count == 1
        assert len(registrar.duplicates) == 0

    def test_duplicate_different_type_recorded(self, registrar, engine):
        b1 = _FakeBridge()
        b2 = _OtherBridge()
        registrar.register("dup", b1)
        registrar.register("dup", b2)
        assert len(registrar.duplicates) >= 1

    def test_duplicate_different_type_logged_not_blocked(self, registrar, engine):
        b1 = _FakeBridge()
        b2 = _OtherBridge()
        registrar.register("dup", b1)
        registrar.register("dup", b2)
        assert registrar.count == 1


# ── Registration with service container ──

class TestRegistrationWithContainer:
    def test_register_binding_uses_container(self, registrar, fake_container):
        binding = ContextBinding(_FakeBridge, "libraryBridge",
                                 required_services=("database", "worker_manager"))
        registrar.register_with_contract(binding, _FakeBridge(), fake_container)
        assert "libraryBridge" in registrar.names

    def test_register_all_bindings(self, registrar, fake_container):
        bindings = [
            ContextBinding(_FakeBridge, "bridgeA", required_services=("database",)),
            ContextBinding(_FakeBridge, "bridgeB", required_services=("playback_service",)),
            ContextBinding(_FakeBridge, "bridgeC"),
        ]
        for b in bindings:
            registrar.register_with_contract(b, _FakeBridge(), fake_container)
        assert registrar.count == 3

    def test_register_binding_missing_container_service_fails(self, registrar, fake_container):
        binding = ContextBinding(_FakeBridge, "failBridge",
                                 required_services=("database", "ghost_service"))
        with pytest.raises(ContractViolation):
            registrar.register_with_contract(binding, _FakeBridge(), fake_container)

    def test_context_bindings_all_have_route_id(self):
        for b in CONTEXT_BINDINGS:
            assert isinstance(b.route_id, str), f"{b.context_name} missing route_id"

    def test_context_bindings_no_none_services(self):
        for b in CONTEXT_BINDINGS:
            for svc in b.required_services:
                assert svc is not None, f"{b.context_name} has None in required_services"
            for svc in b.optional_services:
                assert svc is not None, f"{b.context_name} has None in optional_services"


# ── Canonical map completeness ──

class TestCanonicalMapCompleteness:
    def test_canonical_rules_match_map(self):
        for old, new in CANONICAL_RULES.items():
            assert CANONICAL_MAP[old] == new

    def test_no_legacy_names_in_bindings(self):
        legacy = {"db", "player_service", "search_engine",
                  "sync_manager", "michi_link_controller",
                  "home_audio_controller", "radio_manager"}
        for b in CONTEXT_BINDINGS:
            for svc in list(b.required_services) + list(b.optional_services):
                assert svc not in legacy, (
                    f"{b.context_name} uses legacy name '{svc}'"
                )
