"""Test ApplicationBootstrap — services registry and lifecycles."""
import pytest


def test_bootstrap_creates_container():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    assert b.container is not None


@pytest.mark.skip(reason="Requires full DB setup")
def test_bootstrap_can_run():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    b.run()


def test_bootstrap_has_queue_service():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    b.container.register("queue_service", object())
    qs = b.get_queue_service()
    assert qs is not None


def test_bootstrap_has_worker_manager():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    b.container.register("worker_manager", object())
    wm = b.get_worker_manager()
    assert wm is not None


def test_bootstrap_has_query_executor():
    from core.application_bootstrap import ApplicationBootstrap
    b = ApplicationBootstrap()
    b.container.register("query_executor", object())
    qe = b.get_query_executor()
    assert qe is not None
