"""Missing dependencies are never ignored.

REQUIRED descriptors with a dependency key that is not registered block
bootstrap (validate fails listing the missing key, container -> FAILED).
OPTIONAL descriptors degrade honestly through report_failure instead of
being silently skipped.
"""
from __future__ import annotations

from core.service_container import ContainerState, ServiceContainer
from core.service_manifest import (
    LifecycleKind,
    ServiceClass,
    ServiceDescriptor,
    ServicePriority,
)

MISSING_KEY = "missing_dependency_key"


def _required_manifest() -> dict[str, ServiceDescriptor]:
    return {
        "svc": ServiceDescriptor(
            name="svc",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.REQUIRED,
            dependencies=(MISSING_KEY,),
        ),
    }


def _optional_manifest() -> dict[str, ServiceDescriptor]:
    return {
        "svc": ServiceDescriptor(
            name="svc",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.OPTIONAL,
            dependencies=(MISSING_KEY,),
        ),
    }


def test_validate_fails_for_required_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.service_container.SERVICE_MANIFEST", _required_manifest()
    )
    container = ServiceContainer()
    container.register("svc", object())
    errors = container.validate()
    assert any(MISSING_KEY in error for error in errors)


def test_start_fails_for_required_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.service_container.SERVICE_MANIFEST", _required_manifest()
    )
    container = ServiceContainer()
    container.register("svc", object())
    container.start()
    assert container.state == ContainerState.FAILED


def test_optional_missing_dependency_degrades_not_blocks(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.service_container.SERVICE_MANIFEST", _optional_manifest()
    )
    started = []
    container = ServiceContainer()

    class _Svc:
        def start(self):
            started.append("svc")

    container.register("svc", _Svc())
    container.start()

    assert container.state in (ContainerState.READY, ContainerState.DEGRADED)
    assert started == [], "service with a missing dependency must not start"
    assert container.list_services()["svc"]["failed"] is True
    assert MISSING_KEY in container.list_services()["svc"]["error"]
    assert container.health()["failures"]["svc"]


def test_optional_missing_dependency_reported_not_silent(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.service_container.SERVICE_MANIFEST", _optional_manifest()
    )
    container = ServiceContainer()
    container.register("svc", object())
    container.start()
    assert container.state == ContainerState.DEGRADED
    assert "svc" in container.health()["failures"]
