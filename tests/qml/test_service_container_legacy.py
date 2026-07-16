"""Tests for ServiceContainer real: lifecycle, priorities, capability enforcement."""

from unittest.mock import MagicMock

from core.service_container import ServiceContainer, ServicePriority, ContainerState


def _make_container(**overrides) -> ServiceContainer:
    c = ServiceContainer()
    defaults = {
        "database": MagicMock(),
        "connection_factory": MagicMock(),
        "worker_manager": MagicMock(),
        "query_executor": MagicMock(),
        "job_service": MagicMock(),
        "event_bus": MagicMock(),
        "settings_coordinator": MagicMock(),
        "settings_service": MagicMock(),
        "library_query_service": MagicMock(),
        "library_sources_service": MagicMock(),
        "library_mutation_service": MagicMock(),
        "playlist_service": MagicMock(),
        "history_query_service": MagicMock(),
        "global_search_service": MagicMock(),
        "mix_query_service": MagicMock(),
        "mix_service": MagicMock(),
        "track_action_service": MagicMock(),
        "playback_service": MagicMock(),
        "queue_service": MagicMock(),
        "metadata_service": MagicMock(),
        "theme_service": MagicMock(),
        "accessibility_service": MagicMock(),
        "audio_lab_service": MagicMock(),
        "smart_tagging_service": MagicMock(),
        "library_doctor_service": MagicMock(),
        "device_sync_service": MagicMock(),
        "connection_service": MagicMock(),
        "home_audio_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "notification_service": MagicMock(),
        "action_registry": MagicMock(),
    }
    defaults.update(overrides)
    for name, svc in defaults.items():
        if name in c._all_names():
            c.register(name, svc)
    return c


class TestContainerCreation:
    def test_has_required_services(self):
        c = ServiceContainer()
        required = c._required_names()
        for name in ["database", "connection_factory", "worker_manager", "query_executor", "job_service", "settings_service", "queue_service"]:
            assert name in required, f"{name} missing from required"

    def test_state_initial_created(self):
        c = ServiceContainer()
        assert c.state == ContainerState.CREATED

    def test_all_services_have_priority(self):
        c = ServiceContainer()
        for name in c._all_names():
            assert c.priority(name) is not None

    def test_required_priority_assigned(self):
        c = ServiceContainer()
        for name in c._required_names():
            assert c.priority(name) == ServicePriority.REQUIRED


class TestContainerLifecycle:
    def test_start_to_ready(self):
        c = _make_container()
        c.start()
        assert c.state == ContainerState.READY
        assert c.ready() is True

    def test_start_degraded_on_required_failure(self):
        c = _make_container()
        c.report_failure("connection_factory", "db down")
        assert c.state == ContainerState.CREATED
        assert c.ready() is False

    def test_shutdown_transitions(self):
        c = _make_container()
        c.start()
        c.shutdown()
        assert c.state in (ContainerState.STOPPING, ContainerState.STOPPED)

    def test_shutdown_clears_failures(self):
        c = _make_container()
        c.report_failure("connection_factory", "fail")
        c.shutdown()
        assert not c._failures

    def test_ready_after_start_true(self):
        c = _make_container()
        c.start()
        assert c.ready() is True

    def test_ready_before_start_false(self):
        c = ServiceContainer()
        assert c.ready() is False

    def test_ready_after_shutdown_false(self):
        c = _make_container()
        c.start()
        c.shutdown()
        assert c.ready() is False

    def test_health_returns_state(self):
        c = _make_container()
        c.start()
        h = c.health()
        assert "state" in h
        assert "services" in h
        assert "failures" in h


class TestContainerCapability:
    def test_required_present_is_capable(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        assert c.is_capable("connection_factory") is True

    def test_required_absent_is_not_capable(self):
        c = ServiceContainer()
        assert c.is_capable("connection_factory") is False

    def test_required_failed_is_not_capable(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.report_failure("connection_factory", "error")
        assert c.is_capable("connection_factory") is False


class TestContainerTypedProperties:
    def test_typed_property_worker_manager(self):
        c = ServiceContainer()
        obj = object()
        c.register("worker_manager", obj)
        assert c.worker_manager is obj

    def test_typed_property_returns_none_when_unregistered(self):
        c = ServiceContainer()
        assert c.audio_lab_service is None

    def test_list_services_has_correct_keys(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        info = c.list_services()["connection_factory"]
        assert set(info.keys()) == {"available", "priority", "failed", "error", "capable"}

    def test_list_services_shows_availability(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        listing = c.list_services()
        assert listing["connection_factory"]["available"] is True
        assert listing["theme_service"]["available"] is False
