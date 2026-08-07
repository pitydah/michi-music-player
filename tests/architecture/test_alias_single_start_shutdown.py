"""Aliases share instance and lifecycle: exactly-once start and shutdown.

An alias is declared explicitly via ``alias_of``; it is not an independent
service. One instance registered under two keys (one alias of the other)
starts exactly once and shuts down exactly once.
"""
from __future__ import annotations

from collections import Counter

from core.service_container import ContainerState, ServiceContainer
from core.service_manifest import (
    LifecycleKind,
    ServiceClass,
    ServiceDescriptor,
    ServicePriority,
)


def _alias_manifest() -> dict[str, ServiceDescriptor]:
    return {
        "real": ServiceDescriptor(
            name="real",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.REQUIRED,
        ),
        "alias": ServiceDescriptor(
            name="alias",
            service_class=ServiceClass.DOMAIN_SERVICE,
            lifecycle=LifecycleKind.PASSIVE,
            priority=ServicePriority.OPTIONAL,
            alias_of="real",
        ),
    }


class _RecordingService:
    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()

    def start(self) -> None:
        self.calls["start"] += 1

    def shutdown(self) -> None:
        self.calls["shutdown"] += 1

    def stop(self) -> None:
        self.calls["stop"] += 1


def test_alias_starts_exactly_once(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _alias_manifest())
    service = _RecordingService()
    container = ServiceContainer()
    container.register("real", service)
    container.register("alias", service)

    container.start()

    assert service.calls["start"] == 1
    assert container.state == ContainerState.READY


def test_alias_shuts_down_exactly_once(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _alias_manifest())
    service = _RecordingService()
    container = ServiceContainer()
    container.register("real", service)
    container.register("alias", service)

    container.start()
    container.shutdown()

    assert service.calls["start"] == 1
    assert service.calls["shutdown"] == 1
    assert container.state == ContainerState.STOPPED


def test_alias_is_not_a_lifecycle_node(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _alias_manifest())
    container = ServiceContainer()
    assert "alias" not in container.build_order()
    assert "alias" not in container._lifecycle_start_order()


def test_alias_shutdown_without_start_also_once(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _alias_manifest())
    service = _RecordingService()
    container = ServiceContainer()
    container.register("real", service)
    container.register("alias", service)

    container.shutdown()

    assert service.calls["shutdown"] == 1
    assert service.calls["stop"] == 0


def test_alias_missing_target_reported(monkeypatch) -> None:
    manifest = {
        "alias": ServiceDescriptor(
            name="alias",
            service_class=ServiceClass.DOMAIN_SERVICE,
            lifecycle=LifecycleKind.PASSIVE,
            priority=ServicePriority.OPTIONAL,
            alias_of="no_such_key",
        ),
    }
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", manifest)
    container = ServiceContainer()
    container.register("alias", object())
    warnings = container.manifest_diagnostics()
    assert any("no_such_key" in warning for warning in warnings)
