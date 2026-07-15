"""Tests for ServiceContainer v12 — 28 REQUIRED, single composition, no aliases.

X10.03: ServiceContainer must be the UNICA composicion.
Validates: required_present, dependencies_present, no_none_required, acyclic_graph, build_start_order.
If REQUIRED missing: state=FAILED, start() fails, QML NOT loaded.
"""
from core.service_container import ServiceContainer, ContainerState


REQUIRED_28 = {
    "database", "connection_factory", "worker_manager",
    "query_executor", "job_service", "event_bus",
    "settings_coordinator", "settings_service",
    "library_query_service", "library_sources_service",
    "library_mutation_service", "playlist_service",
    "history_query_service", "global_search_service",
    "mix_query_service", "mix_service",
    "track_action_service", "playback_service",
    "queue_service", "metadata_service",
    "process_controller", "runtime_persistence",
    "theme_service", "accessibility_service",
    "action_registry", "confirmation_service",
    "notification_service", "diagnostics_service",
}

OPTIONAL_8 = {
    "audio_lab_service", "smart_tagging_service",
    "library_doctor_service", "device_sync_service",
    "connection_service", "home_audio_service",
    "radio_service", "lyrics_service",
}

CAPABILITY_GATED = {"michi_ai_service"}

ALL_37 = REQUIRED_28 | OPTIONAL_8 | CAPABILITY_GATED


class TestV12RequiredCount:
    def test_28_required_services(self):
        c = ServiceContainer()
        assert len(c._required_names()) == 28, f"Expected 28, got {len(c._required_names())}"

    def test_8_optional_services(self):
        c = ServiceContainer()
        assert len(c._optional_names()) == 8, f"Expected 8, got {len(c._optional_names())}"

    def test_1_capability_gated(self):
        c = ServiceContainer()
        assert len(c._capability_gated_names()) == 1

    def test_37_total_services(self):
        c = ServiceContainer()
        assert len(c._all_names()) == 37

    def test_required_set_matches_28(self):
        c = ServiceContainer()
        assert c._required_names() == REQUIRED_28

    def test_optional_set_matches_8(self):
        c = ServiceContainer()
        assert c._optional_names() == OPTIONAL_8

    def test_capability_gated_matches(self):
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
        assert len(missing) == 28

    def test_validate_required_present_all_registered(self):
        c = ServiceContainer()
        for name in REQUIRED_28:
            c.register(name, object())
        missing = c.validate_required_present()
        assert missing == []

    def test_validate_no_none_required_empty(self):
        c = ServiceContainer()
        assert len(c.validate_no_none_required()) == 28

    def test_validate_no_none_required_after_register(self):
        c = ServiceContainer()
        for name in REQUIRED_28:
            c.register(name, object())
        assert c.validate_no_none_required() == []

    def test_validate_no_none_required_rejects_none(self):
        c = ServiceContainer()
        for name in REQUIRED_28:
            c.register(name, None)
        bad = c.validate_no_none_required()
        assert len(bad) == 28

    def test_acyclic_graph_valid(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        order = c.validate_acyclic_graph()
        assert len(order) == 37
        assert isinstance(order, list)

    def test_acyclic_graph_raises_on_cycle(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c._dependencies["database"] = ("database",)
        try:
            c.validate_acyclic_graph()
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_build_start_order_returns_list(self):
        c = ServiceContainer()
        for name in REQUIRED_28:
            c.register(name, object())
        order = c.build_start_order()
        assert isinstance(order, list)
        assert len(order) >= 28

    def test_start_order_prioritizes_required(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        order = c.build_start_order()
        required = {n for n in REQUIRED_28}
        seen_optional = False
        for svc in order:
            if svc not in required:
                seen_optional = True
            elif seen_optional:
                pass
        required_first = order[:28]
        for r in required:
            assert r in required_first[:28]

    def test_dependencies_present_valid(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
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
        for name in REQUIRED_28:
            c.register(name, None if name != "database" else object())
        c.start()
        assert c.state == ContainerState.FAILED

    def test_start_succeeds_with_all_required(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c.start()
        assert c.state in (ContainerState.READY, ContainerState.DEGRADED)

    def test_start_ready_state_with_all_required(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c.start()
        assert c.state == ContainerState.READY

    def test_start_degraded_when_optional_fails(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c.report_failure("radio_service", "unavailable")
        c.start()
        assert c.state == ContainerState.DEGRADED

    def test_start_idempotent(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c.start()
        s1 = c.state
        c.start()
        assert c.state == s1


class TestV12Health:
    def test_health_reports_28_required(self):
        c = ServiceContainer()
        h = c.health()
        assert h["required"] == 28

    def test_health_reports_8_optional(self):
        c = ServiceContainer()
        h = c.health()
        assert h["optional"] == 8

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
        for name in ALL_37:
            c.register(name, object())
        c.start()
        h = c.health()
        assert h["state"] == "ready"


class TestV12NoAliases:
    def test_service_container_is_unique_registry(self):
        from core.service_container import ServiceRegistry
        assert ServiceRegistry is ServiceContainer

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
        for name in ALL_37:
            c.register(name, object())
        c.start()
        c.shutdown()
        assert c.state == ContainerState.STOPPED

    def test_cancel_all_does_not_raise(self):
        c = ServiceContainer()
        for name in ALL_37:
            c.register(name, object())
        c.cancel_all()

    def test_shutdown_clears_failures(self):
        c = ServiceContainer()
        c.report_failure("database", "err")
        c.shutdown()
        h = c.health()
        assert h["failures"] == {}
