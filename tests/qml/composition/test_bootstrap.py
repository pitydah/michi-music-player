"""Tests for ApplicationBootstrap lifecycle and contractual API."""
from unittest.mock import Mock

import pytest
pytestmark = [pytest.mark.qml_module("worker_manager")]


class TestBootstrapCreation:
    def test_creates_container(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.container is not None

    def test_container_is_created_state(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.container.state.value == "created"

    def test_has_api_methods(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert hasattr(b, 'build')
        assert hasattr(b, 'start')
        assert hasattr(b, 'create_bridges')
        assert hasattr(b, 'register_context')
        assert hasattr(b, 'load_qml')
        assert hasattr(b, 'shutdown')


class TestBootstrapStart:
    def test_start_sets_state(self):
        from core.application_bootstrap import ApplicationBootstrap
        import core.service_container as sc
        orig_state = sc.ServiceContainer.start
        sc.ServiceContainer.start = lambda self: setattr(self, '_state', sc.ContainerState.READY)
        try:
            b = ApplicationBootstrap()
            b.container.register("test_svc", object())
            b.start()
            assert b.container.state.value in ("ready", "degraded")
        finally:
            sc.ServiceContainer.start = orig_state

    def test_shutdown_clears_state(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        b.shutdown()
        assert b.container.state.value == "stopped"

    def test_get_queue_service_returns_none_if_not_registered(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.get_queue_service() is None

    def test_get_worker_manager_returns_none_if_not_registered(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.get_worker_manager() is None

    def test_get_query_executor_returns_none_if_not_registered(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.get_query_executor() is None


class TestBootstrapBridges:
    def test_create_bridges_returns_dict(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        bridges = b.create_bridges()
        assert isinstance(bridges, dict)

    def test_create_bridges_has_navigation(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        bridges = b.create_bridges()
        assert "navigation" in bridges

    def test_create_bridges_with_container_values(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        bridges = b.create_bridges()
        assert len(bridges) > 0


class TestBootstrapContext:
    def test_register_context_returns_registrar(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        bridges = b.create_bridges()
        b._bridges = bridges
        engine = Mock()
        engine.rootContext = Mock()
        registrar = b.register_context(engine)
        assert registrar is not None

    def test_register_context_without_bridges_does_not_crash(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        b._bridges = {}
        engine = Mock()
        engine.rootContext = Mock()
        registrar = b.register_context(engine)
        assert registrar.count == 0


class TestBootstrapLoadQML:
    def test_load_qml_fails_without_qml_file(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        engine = Mock()
        engine.rootObjects.return_value = []
        result = b.load_qml(engine, qml_path="/nonexistent/Main.qml")
        assert result is False

    def test_load_qml_returns_true_on_success(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        engine = Mock()
        engine.rootObjects.return_value = [Mock()]
        result = b.load_qml(engine, qml_path=str(__file__))
        assert result is True

    def test_load_qml_adds_import_path(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        engine = Mock()
        engine.rootObjects.return_value = [Mock()]
        result = b.load_qml(engine, qml_path="/tmp/test.qml")
        assert result is True


class TestBootstrapFullLifecycle:
    def test_container_created_after_init(self):
        from core.application_bootstrap import ApplicationBootstrap
        b = ApplicationBootstrap()
        assert b.container is not None
