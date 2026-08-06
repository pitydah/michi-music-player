"""Settings cycle resolved: settings_coordinator must NOT depend on settings_service.

Wiring direction is settings_service -> settings_coordinator (settings_service
declares the coordinator as a dependency); the coordinator declares no
dependency on settings_service. The manifest graph (alias-resolved) must be
acyclic.
"""
from __future__ import annotations

from core.service_container import ServiceContainer
from core.service_manifest import SERVICE_MANIFEST


def _manifest_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for name, desc in SERVICE_MANIFEST.items():
        if desc.alias_of is not None:
            continue
        deps = set()
        for dep in desc.dependencies:
            target = SERVICE_MANIFEST.get(dep)
            deps.add(target.alias_of if target and target.alias_of else dep)
        graph[name] = deps
    return graph


def test_coordinator_does_not_depend_on_settings_service() -> None:
    coordinator = SERVICE_MANIFEST["settings_coordinator"]
    assert "settings_service" not in coordinator.dependencies


def test_settings_service_depends_on_coordinator() -> None:
    settings_service = SERVICE_MANIFEST["settings_service"]
    assert "settings_coordinator" in settings_service.dependencies


def test_settings_service_consumes_coordinator() -> None:
    # Consumer metadata mirrors the wiring direction.
    coordinator = SERVICE_MANIFEST["settings_coordinator"]
    assert "settings_service" in coordinator.consumers


def test_full_manifest_graph_is_acyclic() -> None:
    graph = _manifest_graph()
    emitted: set[str] = set()
    order: list[str] = []

    while True:
        progress = False
        for name in graph:
            if name in emitted:
                continue
            if all(dep in emitted or dep not in graph for dep in graph[name]):
                emitted.add(name)
                order.append(name)
                progress = True
        if not progress:
            break

    remaining = [name for name in graph if name not in emitted]
    assert remaining == [], (
        f"manifest graph contains a cycle involving: {remaining}"
    )


def test_settings_subgraph_is_acyclic() -> None:
    """The settings subgraph (coordinator + service + transitive deps) is acyclic."""
    graph = _manifest_graph()
    settings_nodes = {"settings_coordinator", "settings_service"}
    visited: set[str] = set()

    def collect(name: str) -> None:
        if name in visited or name not in graph:
            return
        visited.add(name)
        for dep in graph[name]:
            collect(dep)

    for node in settings_nodes:
        collect(node)
    assert {"settings_coordinator", "settings_service"} <= visited

    emitted: set[str] = set()
    while True:
        progress = False
        for name in sorted(visited):
            if name in emitted:
                continue
            if all(dep in emitted or dep not in visited for dep in graph[name]):
                emitted.add(name)
                progress = True
        if not progress:
            break
    remaining = sorted(visited - emitted)
    assert remaining == [], (
        f"settings subgraph contains a cycle: {remaining}"
    )


def test_settings_start_order_has_coordinator_first() -> None:
    container = ServiceContainer()
    order = container._lifecycle_start_order()
    if "settings_coordinator" not in order or "settings_service" not in order:
        return
    assert order.index("settings_coordinator") < order.index("settings_service")
