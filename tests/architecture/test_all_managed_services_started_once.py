"""Every MANAGED service with a start method is started exactly once."""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ServiceContainer
from core.service_manifest import (
    SERVICE_MANIFEST,
    LifecycleKind,
    ServiceClass,
    ServiceDescriptor,
    ServicePriority,
)


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    instance = QGuiApplication.instance()
    if not instance:
        instance = QGuiApplication(sys.argv)
    return instance


class _FakeContainer(ServiceContainer):
    """Container whose frozen tracked-name lists are empty (unit-testing)."""

    @staticmethod
    def _required_names() -> set[str]:
        return set()

    @staticmethod
    def _optional_names() -> set[str]:
        return set()

    @staticmethod
    def _capability_gated_names() -> set[str]:
        return set()


def _fake_manifest(monkeypatch, names: tuple[str, ...]) -> dict[str, ServiceDescriptor]:
    manifest = {
        name: ServiceDescriptor(
            name=name,
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.OPTIONAL,
            dependencies=(),
        )
        for name in names
    }
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", manifest)
    return manifest


class _StartRecorder:
    def __init__(self):
        self.starts = Counter()

    def make(self, name: str):
        def start(*args, **kwargs):
            self.starts[name] += 1

        return start


def test_unit_managed_start_called_exactly_once(monkeypatch) -> None:
    _fake_manifest(monkeypatch, ("alpha", "beta", "gamma"))
    container = _FakeContainer()
    recorder = _StartRecorder()
    for name in ("alpha", "beta", "gamma"):
        container.register(name, type(name, (), {"start": recorder.make(name)})())

    container.start()

    assert dict(recorder.starts) == {"alpha": 1, "beta": 1, "gamma": 1}


def test_unit_missing_start_method_is_not_an_error(monkeypatch) -> None:
    manifest = _fake_manifest(monkeypatch, ("alpha", "beta"))
    alpha_desc = ServiceDescriptor(
        name="alpha",
        service_class=ServiceClass.MANAGED_SERVICE,
        lifecycle=LifecycleKind.MANAGED,
        priority=ServicePriority.OPTIONAL,
    )
    manifest["alpha"] = alpha_desc  # no start method on the instance
    container = _FakeContainer()
    container.register("alpha", object())
    container.register("beta", type("Beta", (), {"start": lambda self: None})())

    container.start()

    assert container.state.value in ("ready", "degraded")
    assert container._started_order == ["beta"]


def test_real_bootstrap_managed_services_started_once(app) -> None:
    """Real composition: every MANAGED start method runs exactly once."""
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    container = bootstrap.container
    recorder = Counter()

    for name, desc in SERVICE_MANIFEST.items():
        if desc.lifecycle != LifecycleKind.MANAGED:
            continue
        svc = container.get(name)
        if svc is None:
            continue
        method = getattr(svc, desc.start_method, None)
        if not callable(method):
            continue
        original = method
        method_name = desc.start_method

        def wrapper(*args, _n=name, _m=original, **kwargs):
            recorder[_n] += 1
            return _m(*args, **kwargs)

        setattr(svc, method_name, wrapper)

    container.start()

    for name, count in recorder.items():
        assert count == 1, (
            f"MANAGED service '{name}' start called {count} times"
        )
    assert recorder, "No MANAGED start method was recorded during bootstrap"


def test_real_bootstrap_snapserver_and_recognition_started(app) -> None:
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    container = bootstrap.container
    started = set()
    for name in ("recognition_service", "snapserver_manager"):
        svc = container.get(name)
        if svc is None:
            continue
        original = svc.start
        method_name = "start"

        def wrapper(_n=name, _m=original):
            started.add(_n)
            return _m()

        setattr(svc, method_name, wrapper)

    container.start()

    assert "recognition_service" in started, "recognition_service.start() never called"
    assert "snapserver_manager" in started, "snapserver_manager.start() never called"
