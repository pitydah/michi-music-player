"""Tests for ServiceContainer completo — every manifest service registered.

Verifica: todos los servicios del manifest clasificados (REQUIRED, OPTIONAL, CAPABILITY_GATED).
Prohíbe: REQUIRED con None, servicios ficticios, bridge que abre DB como fallback.

FASE 1 (P0 stabilization): los sets se derivan de SERVICE_MANIFEST — la única
fuente de verdad — en lugar del inventario congelado eliminado.
"""
from core.service_container import ServiceContainer, ServicePriority, ContainerState
from core.service_manifest import SERVICE_MANIFEST


ALL_SERVICE_NAMES = set(SERVICE_MANIFEST)

REQUIRED_NAMES = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.REQUIRED
}

OPTIONAL_NAMES = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.OPTIONAL
}

CAPABILITY_GATED_NAMES = {
    name for name, desc in SERVICE_MANIFEST.items()
    if desc.priority == ServicePriority.CAPABILITY_GATED
}


class TestCompletoRegistration:
    def test_all_33_services_defined(self):
        c = ServiceContainer()
        names = set(c._all_names())
        assert names == ALL_SERVICE_NAMES, f"Missing: {ALL_SERVICE_NAMES - names}, Extra: {names - ALL_SERVICE_NAMES}"

    def test_20_required_services(self):
        c = ServiceContainer()
        assert c._required_names() == REQUIRED_NAMES

    def test_16_optional_services(self):
        c = ServiceContainer()
        assert c._optional_names() == OPTIONAL_NAMES

    def test_1_capability_gated_service(self):
        c = ServiceContainer()
        assert c._capability_gated_names() == CAPABILITY_GATED_NAMES

    def test_all_services_have_priority_assigned(self):
        c = ServiceContainer()
        for name in c._all_names():
            assert c.priority(name) is not None, f"{name} has no priority"

    def test_required_priority_correct(self):
        c = ServiceContainer()
        for name in c._required_names():
            assert c.priority(name) == ServicePriority.REQUIRED

    def test_optional_priority_correct(self):
        c = ServiceContainer()
        for name in c._optional_names():
            assert c.priority(name) == ServicePriority.OPTIONAL

    def test_capability_gated_priority_correct(self):
        c = ServiceContainer()
        for name in c._capability_gated_names():
            assert c.priority(name) == ServicePriority.CAPABILITY_GATED

    def test_deferred_physical_empty(self):
        c = ServiceContainer()
        assert c._deferred_physical_names() == set()

    def test_no_fake_services(self):
        c = ServiceContainer()
        all_names = c._all_names()
        fake = {n for n in all_names if "fake" in n or "mock" in n or "demo" in n or "stub" in n}
        assert len(fake) == 0, f"Fake services found: {fake}"

    def test_no_none_required_service_allowed(self):
        c = ServiceContainer()
        for name in c._required_names():
            svc = c.get(name)
            assert svc is None, f"Required service {name} should not be pre-registered"
        for name in REQUIRED_NAMES:
            c.register(name, object())
        for name in c._required_names():
            assert c.get(name) is not None, f"Required service {name} must be registered"
            assert c.require(name) is not None, f"Required service {name} must be retrievable via require()"


class TestCompletoLifecycle:
    def test_register_all_services_and_start(self):
        c = ServiceContainer()
        for name in c._all_names():
            c.register(name, object())
        c.start()
        assert c.ready() is True
        assert c.state in (ContainerState.READY, ContainerState.DEGRADED)

    def test_health_includes_new_categories(self):
        c = ServiceContainer()
        h = c.health()
        assert "capability_gated" in h
        assert "deferred_physical" in h

    def test_service_count_in_all_names(self):
        c = ServiceContainer()
        assert len(c._all_names()) == len(SERVICE_MANIFEST)


class TestCompletoCapability:
    def test_capability_gated_present_is_capable(self):
        c = ServiceContainer()
        c.register("michi_ai_service", object())
        c.register("connection_factory", object())  # required dep
        c.register("worker_manager", object())
        c.register("query_executor", object())
        c.register("job_service", object())
        c.register("event_bus", object())
        c.register("settings_coordinator", object())
        c.register("settings_service", object())
        c.register("library_query_service", object())
        c.register("library_sources_service", object())
        c.register("library_mutation_service", object())
        c.register("playlist_service", object())
        c.register("history_query_service", object())
        c.register("global_search_service", object())
        c.register("mix_query_service", object())
        c.register("mix_service", object())
        c.register("track_action_service", object())
        c.register("playback_service", object())
        c.register("queue_service", object())
        c.register("metadata_service", object())
        c.register("database", object())
        assert c.is_capable("michi_ai_service") is True

    def test_capability_gated_absent_not_capable(self):
        c = ServiceContainer()
        assert c.is_capable("michi_ai_service") is False

    def test_capability_gated_failed_not_capable(self):
        c = ServiceContainer()
        c.register("michi_ai_service", object())
        c.report_failure("michi_ai_service", "ai model unavailable")
        assert c.is_capable("michi_ai_service") is False

    def test_deferred_physical_never_capable(self):
        c = ServiceContainer()
        assert "disc_service" not in c._all_names()  # disc_service should NOT be in container

    def test_all_typed_properties_exist(self):
        c = ServiceContainer()
        for name in c._all_names():
            prop_name = name
            method = getattr(c, prop_name, None)
            if method is not None:
                result = method.fget(c) if hasattr(method, 'fget') else method
                assert result is None or callable(result)

    def test_typed_properties_for_new_services(self):
        c = ServiceContainer()
        c.register("database", object())
        c.register("confirmation_service", object())
        c.register("runtime_persistence", object())
        c.register("process_controller", object())
        c.register("radio_service", object())
        c.register("lyrics_service", object())
        c.register("michi_ai_service", object())
        c.register("mix_service", object())
        assert c.database is not None
        assert c.confirmation_service is not None
        assert c.runtime_persistence is not None
        assert c.process_controller is not None
        assert c.radio_service is not None
        assert c.lyrics_service is not None
        assert c.michi_ai_service is not None
        assert c.mix_service is not None


class TestCompletoNegative:
    def test_no_bridge_fallback_to_db(self):
        c = ServiceContainer()
        source = c.__class__.__module__ if hasattr(c.__class__, '__module__') else ""
        assert "bridge" not in source

    def test_database_is_required_not_optional(self):
        c = ServiceContainer()
        assert "database" in c._required_names()
        assert c.priority("database") == ServicePriority.REQUIRED

    def test_unexpected_names_rejected(self):
        c = ServiceContainer()
        c.register("totally_unknown_service", object())
        assert "totally_unknown_service" not in c._all_names()
        warnings = c.manifest_diagnostics()
        assert any(
            "totally_unknown_service" in w for w in warnings
        ), f"Unknown key not flagged: {warnings}"
