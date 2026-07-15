"""Test ServiceContainer lifecycle — states, start, shutdown, health."""
from core.service_container import ServiceContainer, ContainerState


def _register_all_required(sc):
    for name in sc._required_names():
        sc.register(name, object())


def test_initial_state():
    sc = ServiceContainer()
    assert sc.state == ContainerState.CREATED


def test_start_transitions_to_ready():
    sc = ServiceContainer()
    _register_all_required(sc)
    sc.start()
    assert sc.state == ContainerState.READY


def test_ready_returns_true_after_start():
    sc = ServiceContainer()
    _register_all_required(sc)
    assert not sc.ready()
    sc.start()
    assert sc.ready()


def test_shutdown_transitions_to_stopped():
    sc = ServiceContainer()
    _register_all_required(sc)
    sc.start()
    sc.shutdown()
    assert sc.state == ContainerState.STOPPED


def test_health_after_start():
    sc = ServiceContainer()
    _register_all_required(sc)
    sc.start()
    h = sc.health()
    assert h["state"] == "ready"
    assert h["services"] >= 20


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
