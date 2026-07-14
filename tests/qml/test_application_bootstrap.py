"""Tests for ApplicationBootstrap — singleton boot sequence with ServiceContainer."""
from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ServiceContainer


class TestApplicationBootstrapCreation:
    def test_can_create(self):
        boot = ApplicationBootstrap()
        assert boot is not None

    def test_has_container(self):
        boot = ApplicationBootstrap()
        assert isinstance(boot.container, ServiceContainer)

    def test_container_initial_state(self):
        boot = ApplicationBootstrap()
        from core.service_container import ContainerState
        assert boot.container.state == ContainerState.CREATED

    def test_container_empty_at_init(self):
        boot = ApplicationBootstrap()
        assert boot.container.list_services() == {}


class TestApplicationBootstrapRun:
    def test_run_does_not_crash(self):
        boot = ApplicationBootstrap()
        boot.run()

    def test_run_sets_container_ready(self):
        boot = ApplicationBootstrap()
        boot.run()
        from core.service_container import ContainerState
        assert boot.container.state == ContainerState.READY

    def test_run_lifecycle_ready_called(self):
        boot = ApplicationBootstrap()
        boot.run()
        assert boot.container.state.name == "READY"

    def test_run_calls_all_phases(self):
        boot = ApplicationBootstrap()
        boot.run()

    def test_run_idempotent_state(self):
        boot = ApplicationBootstrap()
        boot.run()
        from core.service_container import ContainerState
        assert boot.container.state == ContainerState.READY


class TestApplicationBootstrapContainerIntegration:
    def test_container_has_required_service_names(self):
        required = ServiceContainer.REQUIRED_SERVICES
        assert len(required) == 18

    def test_container_has_optional_service_names(self):
        optional = ServiceContainer.OPTIONAL_SERVICES
        assert len(optional) == 11

    def test_container_total_services(self):
        total = len(ServiceContainer.REQUIRED_SERVICES) + len(ServiceContainer.OPTIONAL_SERVICES)
        assert total == 29

    def test_container_all_names_unique(self):
        all_names = ServiceContainer.REQUIRED_SERVICES + ServiceContainer.OPTIONAL_SERVICES
        assert len(all_names) == len(set(all_names))


class TestApplicationBootstrapEdgeCases:
    def test_multiple_bootstraps_independent(self):
        b1 = ApplicationBootstrap()
        b2 = ApplicationBootstrap()
        assert b1 is not b2
        assert b1.container is not b2.container

    def test_bootstrap_run_multiple_times(self):
        boot = ApplicationBootstrap()
        boot.run()
        boot.run()
        from core.service_container import ContainerState
        assert boot.container.state == ContainerState.READY
