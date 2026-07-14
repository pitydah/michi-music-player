"""Tests for ServiceContainer lifecycle — states, dependencies, health, shutdown."""
import pytest
from core.service_container import ServiceContainer, ContainerState, ServiceLifecycle


class TestContainerStates:
    def test_initial_state_is_created(self):
        c = ServiceContainer()
        assert c.state == ContainerState.CREATED

    def test_start_transitions_to_ready(self):
        c = ServiceContainer()
        svc = ServiceLifecycle()
        c.register("worker_manager", svc)
        c.start()
        assert c.state == ContainerState.READY

    def test_start_with_failure_goes_degraded(self):
        c = ServiceContainer()
        class FailingService(ServiceLifecycle):
            def start(self):
                raise RuntimeError("fail")
        c.register("theme_service", FailingService())
        c.start()
        assert c.state == ContainerState.DEGRADED

    def test_start_with_required_failure_goes_failed(self):
        c = ServiceContainer()
        class FailingRequired(ServiceLifecycle):
            def start(self):
                raise RuntimeError("required fail")
        c.register("worker_manager", FailingRequired())
        c.start()
        assert c.state == ContainerState.FAILED

    def test_cannot_start_twice(self):
        c = ServiceContainer()
        c.register("worker_manager", ServiceLifecycle())
        c.start()
        with pytest.raises(RuntimeError):
            c.start()

    def test_stop_from_ready(self):
        c = ServiceContainer()
        svc = ServiceLifecycle()
        c.register("worker_manager", svc)
        c.start()
        c.stop()
        assert c.state == ContainerState.STOPPED

    def test_stop_from_degraded(self):
        c = ServiceContainer()
        class FailingService(ServiceLifecycle):
            def start(self):
                raise RuntimeError("fail")
        c.register("theme_service", FailingService())
        c.start()
        assert c.state == ContainerState.DEGRADED
        c.stop()
        assert c.state == ContainerState.STOPPED


class TestServiceLifecycle:
    def test_service_lifecycle_defaults(self):
        s = ServiceLifecycle()
        s.start()
        assert s.ready() is True
        assert s.health() is True
        s.shutdown()

    def test_service_health_check(self):
        s = ServiceLifecycle()
        assert s.health() is True

    def test_service_shutdown(self):
        s = ServiceLifecycle()
        s.shutdown()


class TestDependencyGraph:
    def test_simple_dependency(self):
        c = ServiceContainer()
        a = ServiceLifecycle()
        b = ServiceLifecycle()
        c.register("a", a)
        c.register("b", b, dependencies=["a"])
        c.start()
        assert c.state == ContainerState.READY

    def test_circular_dependency_detected(self):
        c = ServiceContainer()
        a = ServiceLifecycle()
        b = ServiceLifecycle()
        c.register("a", a, dependencies=["b"])
        c.register("b", b, dependencies=["a"])
        with pytest.raises(RuntimeError, match="Circular dependency"):
            c.start()

    def test_transitive_dependency(self):
        c = ServiceContainer()
        a = ServiceLifecycle()
        b = ServiceLifecycle()
        cc = ServiceLifecycle()
        c.register("a", a)
        c.register("b", b, dependencies=["a"])
        c.register("cc", cc, dependencies=["b"])
        c.start()
        assert c.state == ContainerState.READY

    def test_topological_order_respected(self):
        c = ServiceContainer()
        order = []
        class OrderedService(ServiceLifecycle):
            def __init__(self, name):
                self._name = name
            def start(self):
                order.append(self._name)
        c.register("a", OrderedService("a"))
        c.register("b", OrderedService("b"), dependencies=["a"])
        c.register("c", OrderedService("c"), dependencies=["b"])
        c.start()
        assert order == ["a", "b", "c"]


class TestHealthAndShutdown:
    def test_health_returns_true_when_all_healthy(self):
        c = ServiceContainer()
        c.register("worker_manager", ServiceLifecycle())
        c.start()
        assert c.health() is True

    def test_shutdown_calls_all_services(self):
        c = ServiceContainer()
        shutdown_called = []
        class TrackedService(ServiceLifecycle):
            def shutdown(self):
                shutdown_called.append("called")
        c.register("worker_manager", TrackedService())
        c.start()
        c.stop()
        assert len(shutdown_called) == 1

    def test_shutdown_reverse_order(self):
        c = ServiceContainer()
        shutdown_order = []
        class TrackedService(ServiceLifecycle):
            def __init__(self, name):
                self._name = name
            def shutdown(self):
                shutdown_order.append(self._name)
        c.register("a", TrackedService("a"))
        c.register("b", TrackedService("b"), dependencies=["a"])
        c.start()
        c.stop()
        assert shutdown_order == ["b", "a"]

    def test_list_services_after_start(self):
        c = ServiceContainer()
        c.register("worker_manager", ServiceLifecycle())
        c.start()
        svcs = c.list_services()
        assert "worker_manager" in svcs
        assert svcs["worker_manager"]["state"] == "READY"
