"""Tests for ServiceRegistry lifecycle, priorities, and capability enforcement."""

from core.service_container import ServiceRegistry, ServicePriority


class TestServiceRegistryCreation:
    def test_has_all_required_services_defined(self):
        reg = ServiceRegistry()
        required = reg._required_names()
        expected = {
            "connection_factory", "worker_manager", "query_executor",
            "job_service", "event_bus", "settings_coordinator",
            "settings_service", "library_query_service",
            "library_sources_service", "library_mutation_service",
            "playlist_service", "history_query_service",
            "global_search_service", "mix_query_service",
            "track_action_service", "playback_service",
            "queue_service", "metadata_service",
        }
        assert required == expected

    def test_has_all_optional_services_defined(self):
        reg = ServiceRegistry()
        optional = reg._optional_names()
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
        reg = ServiceRegistry()
        all_names = reg._all_names()
        for name in all_names:
            assert reg.priority(name) is not None, f"{name} has no priority"

    def test_required_priority_assigned(self):
        reg = ServiceRegistry()
        for name in reg._required_names():
            assert reg.priority(name) == ServicePriority.REQUIRED

    def test_optional_priority_assigned(self):
        reg = ServiceRegistry()
        for name in reg._optional_names():
            assert reg.priority(name) == ServicePriority.OPTIONAL

    def test_deferred_priority_assigned(self):
        reg = ServiceRegistry()
        for name in reg._deferred_names():
            assert reg.priority(name) == ServicePriority.DEFERRED


class TestServiceRegistryTypedProperties:
    def test_typed_property_connection_factory(self):
        reg = ServiceRegistry()
        obj = object()
        reg.register("connection_factory", obj)
        assert reg.connection_factory is obj

    def test_typed_property_worker_manager(self):
        reg = ServiceRegistry()
        obj = object()
        reg.register("worker_manager", obj)
        assert reg.worker_manager is obj

    def test_typed_property_returns_none_when_unregistered(self):
        reg = ServiceRegistry()
        assert reg.audio_lab_service is None


class TestServiceRegistryLifecycle:
    def test_start_sets_started_true(self):
        reg = ServiceRegistry()
        assert reg.ready() is False
        reg.start()
        assert reg.ready() is True

    def test_ready_after_start(self):
        reg = ServiceRegistry()
        reg.start()
        assert reg.ready() is True

    def test_shutdown_resets_started(self):
        reg = ServiceRegistry()
        reg.start()
        reg.shutdown()
        assert reg.ready() is False

    def test_shutdown_clears_failures(self):
        reg = ServiceRegistry()
        reg.report_failure("connection_factory", "fail")
        assert reg._failures
        reg.shutdown()
        assert not reg._failures


class TestServiceRegistryCapability:
    def test_required_present_is_capable(self):
        reg = ServiceRegistry()
        reg.register("connection_factory", object())
        assert reg.is_capable("connection_factory") is True

    def test_required_absent_is_not_capable(self):
        reg = ServiceRegistry()
        assert reg.is_capable("connection_factory") is False

    def test_required_failed_is_not_capable(self):
        reg = ServiceRegistry()
        reg.register("connection_factory", object())
        reg.report_failure("connection_factory", "error")
        assert reg.is_capable("connection_factory") is False

    def test_optional_absent_is_not_capable(self):
        reg = ServiceRegistry()
        assert reg.is_capable("theme_service") is False

    def test_optional_present_is_capable(self):
        reg = ServiceRegistry()
        reg.register("theme_service", object())
        assert reg.is_capable("theme_service") is True

    def test_required_failure_logs_and_blocks_domain(self):
        reg = ServiceRegistry()
        reg.register("connection_factory", object())
        reg.report_failure("connection_factory", "db connection lost")
        assert reg.is_capable("connection_factory") is False
        svc_info = reg.list_services()["connection_factory"]
        assert svc_info["capable"] is False
        assert svc_info["failed"] is True
        assert "db connection lost" in svc_info["error"]


class TestServiceRegistryList:
    def test_list_services_returns_all(self):
        reg = ServiceRegistry()
        listing = reg.list_services()
        assert len(listing) == len(reg._all_names())

    def test_list_services_has_correct_keys(self):
        reg = ServiceRegistry()
        reg.register("connection_factory", object())
        info = reg.list_services()["connection_factory"]
        assert set(info.keys()) == {"available", "priority", "failed", "error", "capable"}

    def test_list_services_shows_availability(self):
        reg = ServiceRegistry()
        reg.register("connection_factory", object())
        reg.register("worker_manager", object())
        listing = reg.list_services()
        assert listing["connection_factory"]["available"] is True
        assert listing["worker_manager"]["available"] is True
        assert listing["theme_service"]["available"] is False
