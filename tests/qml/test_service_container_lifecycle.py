"""Test ServiceContainer lifecycle — states, start, shutdown, health."""
from core.service_container import ServiceRegistry as ServiceContainer, ContainerState


def test_initial_state():
    sc = ServiceContainer()
    assert sc.state == ContainerState.CREATED


def test_start_transitions_to_ready():
    sc = ServiceContainer()
    sc.register("test_svc", object())
    sc.start()
    assert sc.state == ContainerState.READY


def test_ready_returns_true_after_start():
    sc = ServiceContainer()
    sc.register("test_svc", object())
    assert not sc.ready()
    sc.start()
    assert sc.ready()


def test_shutdown_transitions_to_stopped():
    sc = ServiceContainer()
    sc.register("test_svc", object())
    sc.start()
    sc.shutdown()
    assert sc.state == ContainerState.STOPPED


def test_health_after_start():
    sc = ServiceContainer()
    sc.register("connection_factory", object())
    sc.register("worker_manager", object())
    sc.register("query_executor", object())
    sc.register("job_service", object())
    sc.register("settings_service", object())
    sc.register("library_query_service", object())
    sc.register("playlist_service", object())
    sc.register("queue_service", object())
    sc.register("metadata_service", object())
    sc.start()
    h = sc.health()
    assert h["state"] == "ready"
    assert h["services"] >= 9


def test_register_and_get():
    sc = ServiceContainer()
    obj = {"name": "test"}
    sc.register("test_key", obj)
    assert sc.get("test_key") is obj


def test_required_failure_shows_in_health():
    sc = ServiceContainer()
    sc.report_failure("connection_factory", "DB connection refused")
    h = sc.health()
    assert "connection_factory" in h["failures"]
