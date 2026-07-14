"""Tests for ServiceContainer lifecycle, priorities, and capability enforcement."""

from core.service_container import ServiceContainer, ServicePriority


class TestContainerCreation:
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
            "mix_query_service", "track_action_service",
            "playback_service", "queue_service", "metadata_service",
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
            "diagnostics_service", "notification_service",
            "action_registry",
        }
        assert optional == expected

    def test_all_services_have_priority(self):
        c = ServiceContainer()
        all_names = c._all_names()
        for name in all_names:
            assert c.priority(name) is not None

    def test_required_priority_assigned(self):
        c = ServiceContainer()
        for name in c._required_names():
            assert c.priority(name) == ServicePriority.REQUIRED

    def test_optional_priority_assigned(self):
        c = ServiceContainer()
        for name in c._optional_names():
            assert c.priority(name) == ServicePriority.OPTIONAL

    def test_deferred_priority_assigned(self):
        c = ServiceContainer()
        for name in c._deferred_names():
            assert c.priority(name) == ServicePriority.DEFERRED


class TestContainerTypedProperties:
    def test_typed_property_connection_factory(self):
        c = ServiceContainer()
        obj = object()
        c.register("connection_factory", obj)
        assert c.connection_factory is obj

    def test_typed_property_worker_manager(self):
        c = ServiceContainer()
        obj = object()
        c.register("worker_manager", obj)
        assert c.worker_manager is obj

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
