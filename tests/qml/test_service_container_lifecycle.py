"""Test ServiceContainer lifecycle — states, start, shutdown, health."""
from core.service_container import ServiceContainer, ContainerState
from core.service_manifest import SERVICE_MANIFEST, ServicePriority


def _manifest_start_keys() -> set[str]:
    """Every REQUIRED manifest key plus its transitive declared dependencies.

    FASE 1: validation fails when a REQUIRED descriptor's dependency is
    missing, so the fixture registers the closure (SERVICE_MANIFEST is the
    single source of truth — no frozen name lists).
    """
    needed = {
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.priority == ServicePriority.REQUIRED
    }
    changed = True
    while changed:
        changed = False
        for name, desc in SERVICE_MANIFEST.items():
            if name in needed:
                for dep in desc.dependencies:
                    if dep not in needed:
                        needed.add(dep)
                        changed = True
    return needed


def _register_all_required(sc):
    instances = {}
    for name in _manifest_start_keys():
        desc = SERVICE_MANIFEST[name]
        if desc.alias_of is None:
            instances[name] = object()
    for name in _manifest_start_keys():
        desc = SERVICE_MANIFEST[name]
        if desc.alias_of is not None:
            instances[name] = instances[desc.alias_of]
    for name, svc in instances.items():
        sc.register(name, svc)


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
