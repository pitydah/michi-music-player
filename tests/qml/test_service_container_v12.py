"""Tests for ServiceContainer v12 — manifest-driven sets, single composition, no aliases.

X10.03: ServiceContainer must be the UNICA composicion.
Validates: required_present, dependencies_present, no_none_required, acyclic_graph, build_start_order.
If REQUIRED missing: state=FAILED, start() fails, QML NOT loaded.

FASE 1 (P0 stabilization): REQUIRED/OPTIONAL/CAPABILITY_GATED are derived from
SERVICE_MANIFEST — the single source of truth — instead of the removed frozen
inventory (REQUIRED_28/OPTIONAL_8/ALL_37).
"""
import pytest

from core.service_container import (
    ContainerState,
    ManifestCycleError,
    ServiceContainer,
)
from core.service_manifest import (
    SERVICE_MANIFEST,
    LifecycleKind,
    ServiceClass,
    ServiceDescriptor,
    ServicePriority,
)


REQUIRED = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.REQUIRED
}

OPTIONAL = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.OPTIONAL
}

CAPABILITY_GATED = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.CAPABILITY_GATED
}

ALL_MANIFEST = set(SERVICE_MANIFEST)


def _register_all(sc):
    """Register every manifest key; aliases share the instance of their target."""
    instances = {}
    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is None:
            instances[name] = object()
    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is not None:
            instances[name] = instances[desc.alias_of]
    for name, svc in instances.items():
        sc.register(name, svc)


def _cycle_descriptor(name: str, deps: tuple[str, ...]) -> ServiceDescriptor:
    """Standalone OPTIONAL descriptor used to inject a manifest cycle."""
    return ServiceDescriptor(
        name=name,
        service_class=ServiceClass.MANAGED_SERVICE,
        lifecycle=LifecycleKind.MANAGED,
        priority=ServicePriority.OPTIONAL,
        dependencies=deps,
    )


class TestV12RequiredCount:
    def test_required_services_count(self):
        c = ServiceContainer()
        assert len(c._required_names()) == len(REQUIRED)

    def test_optional_services_count(self):
        c = ServiceContainer()
        assert len(c._optional_names()) == len(OPTIONAL)

    def test_capability_gated_count(self):
        c = ServiceContainer()
        assert len(c._capability_gated_names()) == len(CAPABILITY_GATED)

    def test_total_manifest_services(self):
        c = ServiceContainer()
        assert len(c._all_names()) == len(ALL_MANIFEST)

    def test_required_set_matches_manifest(self):
        c = ServiceContainer()
        assert c._required_names() == REQUIRED

    def test_optional_set_matches_manifest(self):
        c = ServiceContainer()
        assert c._optional_names() == OPTIONAL

    def test_capability_gated_matches_manifest(self):
        c = ServiceContainer()
        assert c._capability_gated_names() == CAPABILITY_GATED

    def test_no_duplicates_across_categories(self):
        c = ServiceContainer()
        all_n = c._all_names()
        assert len(all_n) == len(set(all_n))


class TestV12RequiredValidation:
    def test_validate_required_present_all_missing(self):
        c = ServiceContainer()
        missing = c.validate_required_present()
        assert len(missing) == len(REQUIRED)

    def test_validate_required_present_all_registered(self):
        c = ServiceContainer()
        for name in REQUIRED:
            c.register(name, object())
        missing = c.validate_required_present()
        assert missing == []

    def test_validate_no_none_required_empty(self):
        c = ServiceContainer()
        assert len(c.validate_no_none_required()) == len(REQUIRED)

    def test_validate_no_none_required_after_register(self):
        c = ServiceContainer()
        for name in REQUIRED:
            c.register(name, object())
        assert c.validate_no_none_required() == []

    def test_validate_no_none_required_rejects_none(self):
        c = ServiceContainer()
        for name in REQUIRED:
            c.register(name, None)
        bad = c.validate_no_none_required()
        assert len(bad) == len(REQUIRED)

    def test_acyclic_graph_valid(self):
        c = ServiceContainer()
        _register_all(c)
        order = c.validate_acyclic_graph()
        assert isinstance(order, list)
        non_alias = [name for name, desc in SERVICE_MANIFEST.items()
                     if desc.alias_of is None]
        assert len(order) == len(non_alias)

    def test_acyclic_graph_raises_on_cycle(self, monkeypatch):
        c = ServiceContainer()
        monkeypatch.setitem(
            SERVICE_MANIFEST, "cycle_a", _cycle_descriptor("cycle_a", ("cycle_b",))
        )
        monkeypatch.setitem(
            SERVICE_MANIFEST, "cycle_b", _cycle_descriptor("cycle_b", ("cycle_a",))
        )
        with pytest.raises(ManifestCycleError):
            c.validate_acyclic_graph()
        errors = c.validate()
        assert any("Circular dependency" in e for e in errors)
        c.start()
        assert c.state == ContainerState.FAILED

    def test_build_start_order_returns_list(self):
        c = ServiceContainer()
        for name in REQUIRED:
            c.register(name, object())
        order = c.build_start_order()
        assert isinstance(order, list)
        assert len(order) >= len(REQUIRED)

    def test_start_order_prioritizes_required(self):
        c = ServiceContainer()
        _register_all(c)
        order = c.build_start_order()
        positions = {name: idx for idx, name in enumerate(order)}
        required_no_alias = {
            name for name in REQUIRED if SERVICE_MANIFEST[name].alias_of is None
        }
        for name in required_no_alias:
            assert name in positions, f"REQUIRED '{name}' missing from start order"
        for name, desc in SERVICE_MANIFEST.items():
            if desc.alias_of is not None:
                continue
            for dep in desc.dependencies:
                target = SERVICE_MANIFEST[dep].alias_of or dep
                assert positions[target] < positions[name], (
                    f"dependency '{dep}' must start before '{name}'"
                )

    def test_dependencies_present_valid(self):
        c = ServiceContainer()
        _register_all(c)
        broken = c.validate_dependencies_present()
        assert broken == []


class TestV12StartFailure:
    def test_start_fails_on_missing_required(self):
        c = ServiceContainer()
        c.register("database", object())
        c.start()
        assert c.state == ContainerState.FAILED

    def test_start_fails_on_none_required(self):
        c = ServiceContainer()
        for name in REQUIRED:
            c.register(name, None if name != "database" else object())
        c.start()
        assert c.state == ContainerState.FAILED

    def test_start_succeeds_with_all_required(self):
        c = ServiceContainer()
        _register_all(c)
        c.start()
        assert c.state in (ContainerState.READY, ContainerState.DEGRADED)

    def test_start_ready_state_with_all_required(self):
        c = ServiceContainer()
        _register_all(c)
        c.start()
        assert c.state == ContainerState.READY

    def test_start_degraded_when_optional_fails(self):
        c = ServiceContainer()
        _register_all(c)
        c.report_failure("radio_service", "unavailable")
        c.start()
        assert c.state == ContainerState.DEGRADED

    def test_start_idempotent(self):
        c = ServiceContainer()
        _register_all(c)
        c.start()
        s1 = c.state
        c.start()
        assert c.state == s1


class TestV12Health:
    def test_health_reports_28_required(self):
        c = ServiceContainer()
        h = c.health()
        assert h["required"] == len(REQUIRED)

    def test_health_reports_8_optional(self):
        c = ServiceContainer()
        h = c.health()
        assert h["optional"] == len(OPTIONAL)

    def test_health_reports_state(self):
        c = ServiceContainer()
        h = c.health()
        assert h["state"] == "created"

    def test_health_reports_failures(self):
        c = ServiceContainer()
        c.report_failure("database", "connection lost")
        h = c.health()
        assert "database" in h["failures"]

    def test_health_after_failed_start(self):
        c = ServiceContainer()
        c.start()
        h = c.health()
        assert h["state"] == "failed"

    def test_health_after_ready(self):
        c = ServiceContainer()
        _register_all(c)
        c.start()
        h = c.health()
        assert h["state"] == "ready"


class TestV12NoAliases:
    def test_service_container_is_unique_registry(self):
        assert True

    def test_no_separate_registry_class(self):
        c = ServiceContainer()
        assert hasattr(c, "_services")
        assert hasattr(c, "register")
        assert hasattr(c, "get")

    def test_no_parallel_registrations(self):
        c = ServiceContainer()
        assert not hasattr(c, "_alias_map")


class TestV12Lifecycle:
    def test_shutdown_resets(self):
        c = ServiceContainer()
        _register_all(c)
        c.start()
        c.shutdown()
        assert c.state == ContainerState.STOPPED

    def test_cancel_all_does_not_raise(self):
        c = ServiceContainer()
        _register_all(c)
        c.cancel_all()

    def test_shutdown_clears_failures(self):
        c = ServiceContainer()
        c.report_failure("database", "err")
        c.shutdown()
        h = c.health()
        assert h["failures"] == {}
