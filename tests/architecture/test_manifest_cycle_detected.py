"""A cycle in the manifest dependency graph MUST fail bootstrap explicitly.

The cycle path is reported, the container transitions to FAILED, and there is
no hang and no silent fallback.
"""
from __future__ import annotations

import pytest

from core.service_container import ContainerState, ManifestCycleError, ServiceContainer
from core.service_manifest import (
    LifecycleKind,
    ServiceClass,
    ServiceDescriptor,
    ServicePriority,
)


def _cycle_manifest() -> dict[str, ServiceDescriptor]:
    return {
        "a": ServiceDescriptor(
            name="a",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.REQUIRED,
            dependencies=("b",),
        ),
        "b": ServiceDescriptor(
            name="b",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.REQUIRED,
            dependencies=("a",),
        ),
    }


def _registered_container() -> ServiceContainer:
    container = ServiceContainer()
    container.register("a", object())
    container.register("b", object())
    return container


def test_validate_reports_cycle(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _cycle_manifest())
    errors = _registered_container().validate()
    assert any("Circular dependency" in error for error in errors)


def test_validate_lists_cycle_path(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _cycle_manifest())
    errors = _registered_container().validate()
    reported = " ".join(errors)
    assert "a" in reported and "b" in reported


def test_start_fails_container_on_cycle(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _cycle_manifest())
    container = _registered_container()
    container.start()
    assert container.state == ContainerState.FAILED
    assert not container.ready()


def test_build_order_raises_manifest_cycle_error(monkeypatch) -> None:
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _cycle_manifest())
    with pytest.raises(ManifestCycleError):
        _registered_container().build_order()


def test_cycle_detection_does_not_hang(monkeypatch) -> None:
    """Cycle detection must terminate immediately (no infinite loop)."""
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", _cycle_manifest())
    container = _registered_container()
    container.start()
    assert container.state == ContainerState.FAILED
