"""Tests for ServiceContainer lifecycle, priorities, and capability enforcement.

15+ tests covering: register, get, require, contains, start, health, cancel_all, shutdown.
States: CREATEDBUILDINGBUILTSTARTINGREADYDEGRADEDFAILEDSTOPPINGSTOPPED.
"""
from unittest.mock import Mock
from core.service_container import ServiceContainer, ServicePriority, ContainerState
import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestContainerCreation:
    def test_initial_state_is_created(self):
        c = ServiceContainer()
        assert c.state == ContainerState.CREATED

    def test_has_all_required_services_defined(self):
        c = ServiceContainer()
        required = c._required_names()
        expected = {
            "database", "connection_factory", "worker_manager",
            "query_executor", "job_service", "event_bus",
            "settings_coordinator", "settings_service",
            "library_query_service", "library_sources_service",
            "library_mutation_service", "playlist_service",
            "history_query_service", "global_search_service",
            "mix_query_service", "mix_service",
            "track_action_service", "playback_service",
            "queue_service", "metadata_service",
        }
        assert required == expected

    def test_has_all_optional_services_defined(self):
        c = ServiceContainer()
        optional = c._optional_names()
        expected = {
            "theme_service", "accessibility_service",
            "audio_lab_service", "smart_tagging_service",
            "library_doctor_service", "device_sync_service",
            "connection_service", "home_audio_service",
            "radio_service", "lyrics_service",
            "diagnostics_service", "notification_service",
            "action_registry", "confirmation_service",
            "runtime_persistence", "process_controller",
        }
        assert optional == expected

    def test_all_services_have_priority(self):
        c = ServiceContainer()
        for name in c._all_names():
            assert c.priority(name) is not None

    def test_required_priority_assigned(self):
        c = ServiceContainer()
        for name in c._required_names():
            assert c.priority(name) == ServicePriority.REQUIRED

    def test_optional_priority_assigned(self):
        c = ServiceContainer()
        for name in c._optional_names():
            assert c.priority(name) == ServicePriority.OPTIONAL


class TestContainerAPI:
    def test_register_and_get(self):
        c = ServiceContainer()
        obj = object()
        c.register("test_svc", obj)
        assert c.get("test_svc") is obj

    def test_require_returns_service(self):
        c = ServiceContainer()
        obj = object()
        c.register("test_svc", obj)
        assert c.require("test_svc") is obj

    def test_require_raises_on_missing(self):
        c = ServiceContainer()
        with pytest.raises(KeyError):
            c.require("nonexistent")

    def test_contains_returns_true(self):
        c = ServiceContainer()
        c.register("test_svc", object())
        assert c.contains("test_svc") is True

    def test_contains_returns_false_for_unregistered(self):
        c = ServiceContainer()
        assert c.contains("nonexistent") is False

    def test_register_with_required_flag(self):
        c = ServiceContainer()
        c.register("custom", object(), required=True)
        assert c.priority("custom") == ServicePriority.REQUIRED

    def test_register_with_dependencies(self):
        c = ServiceContainer()
        c.register("a", object(), dependencies=("b",))
        assert c._dependencies["a"] == ("b",)

    def test_typed_property_connection_factory(self):
        c = ServiceContainer()
        obj = object()
        c.register("connection_factory", obj)
        assert c.connection_factory is obj

    def test_typed_property_returns_none_when_unregistered(self):
        c = ServiceContainer()
        assert c.audio_lab_service is None


class TestContainerLifecycle:
    def test_start_sets_ready(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.start()
        assert c.ready() is True

    def test_shutdown_resets_state(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.start()
        c.shutdown()
        assert c.ready() is False

    def test_shutdown_clears_failures(self):
        c = ServiceContainer()
        c.report_failure("connection_factory", "fail")
        assert c._failures
        c.shutdown()
        assert not c._failures

    def test_shutdown_state_is_stopped(self):
        c = ServiceContainer()
        c.shutdown()
        assert c.state == ContainerState.STOPPED

    def test_cancel_all_does_not_crash(self):
        c = ServiceContainer()
        c.register("test_svc", object())
        c.cancel_all()

    def test_cancel_all_calls_cancel_on_cancellable(self):
        c = ServiceContainer()
        svc = Mock()
        svc.cancel = Mock()
        c.register("cancellable_svc", svc)
        c.cancel_all()
        svc.cancel.assert_called_once()


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

    def test_optional_absent_is_not_capable(self):
        c = ServiceContainer()
        assert c.is_capable("theme_service") is False

    def test_optional_present_is_capable(self):
        c = ServiceContainer()
        c.register("theme_service", object())
        assert c.is_capable("theme_service") is True

    def test_required_failure_logs_and_blocks_domain(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.report_failure("connection_factory", "db connection lost")
        assert c.is_capable("connection_factory") is False
        svc_info = c.list_services()["connection_factory"]
        assert svc_info["capable"] is False
        assert svc_info["failed"] is True
        assert "db connection lost" in svc_info["error"]


class TestContainerList:
    def test_list_services_returns_all(self):
        c = ServiceContainer()
        listing = c.list_services()
        assert len(listing) == len(c._all_names())

    def test_list_services_has_correct_keys(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        info = c.list_services()["connection_factory"]
        assert set(info.keys()) == {"available", "priority", "failed", "error", "capable"}

    def test_list_services_shows_availability(self):
        c = ServiceContainer()
        c.register("connection_factory", object())
        c.register("worker_manager", object())
        listing = c.list_services()
        assert listing["connection_factory"]["available"] is True
        assert listing["worker_manager"]["available"] is True
        assert listing["theme_service"]["available"] is False


class TestContainerHealth:
    def test_health_returns_dict(self):
        c = ServiceContainer()
        h = c.health()
        assert isinstance(h, dict)

    def test_health_has_state_key(self):
        c = ServiceContainer()
        assert "state" in c.health()

    def test_health_has_services_count(self):
        c = ServiceContainer()
        assert "services" in c.health()
