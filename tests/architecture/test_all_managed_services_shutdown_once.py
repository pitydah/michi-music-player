"""Every MANAGED service is shut down exactly once, in reverse start order."""
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
    @staticmethod
    def _required_names() -> set[str]:
        return set()

    @staticmethod
    def _optional_names() -> set[str]:
        return set()

    @staticmethod
    def _capability_gated_names() -> set[str]:
        return set()


@pytest.mark.gate
def test_unit_managed_shutdown_once_in_reverse_order(monkeypatch) -> None:
    manifest = {
        name: ServiceDescriptor(
            name=name,
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.OPTIONAL,
            dependencies=(),
        )
        for name in ("alpha", "beta", "gamma")
    }
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", manifest)
    container = _FakeContainer()
    started: list[str] = []
    shutdowns: list[str] = []
    for name in ("alpha", "beta", "gamma"):
        container.register(
            name,
            type(
                name,
                (),
                {
                    "start": (lambda *a, _n=name: started.append(_n)),
                    "shutdown": (lambda *a, _n=name: shutdowns.append(_n)),
                },
            )(),
        )

    container.start()
    container.shutdown()

    assert started == ["alpha", "beta", "gamma"]
    # Reverse of the start order (alpha, beta, gamma).
    assert shutdowns == ["gamma", "beta", "alpha"]
    assert len(shutdowns) == 3  # each MANAGED instance shut down exactly once


@pytest.mark.gate
def test_unit_stop_fallback_called_once(monkeypatch) -> None:
    manifest = {
        "only_stop": ServiceDescriptor(
            name="only_stop",
            service_class=ServiceClass.MANAGED_SERVICE,
            lifecycle=LifecycleKind.MANAGED,
            priority=ServicePriority.OPTIONAL,
            dependencies=(),
            shutdown_method="shutdown",
            stop_method="stop",
        ),
    }
    monkeypatch.setattr("core.service_container.SERVICE_MANIFEST", manifest)
    container = _FakeContainer()
    stops = Counter()
    container.register(
        "only_stop",
        type(
            "OnlyStop",
            (),
            {"stop": (lambda *a: stops.__setitem__("only_stop", stops["only_stop"] + 1))},
        )(),
    )

    container.shutdown()

    assert stops["only_stop"] == 1


def _counting(counter: Counter[str], name: str, method):
    """Return a wrapper that records one call for *name* before delegating."""

    def wrapper(*args, **kwargs):
        counter[name] += 1
        return method(*args, **kwargs)

    return wrapper


@pytest.mark.gate
def test_real_bootstrap_managed_shutdown_once(app) -> None:
    """Real composition: every MANAGED shutdown/stop runs exactly once."""
    bootstrap = ApplicationBootstrap()
    bootstrap.build()
    container = bootstrap.container
    shutdown_calls: Counter[str] = Counter()
    stop_calls: Counter[str] = Counter()

    for name, desc in SERVICE_MANIFEST.items():
        if desc.lifecycle != LifecycleKind.MANAGED:
            continue
        svc = container.get(name)
        if svc is None:
            continue
        shutdown_method = getattr(svc, desc.shutdown_method, None)
        if callable(shutdown_method):
            setattr(
                svc,
                desc.shutdown_method,
                _counting(shutdown_calls, name, shutdown_method),
            )
        stop_method = getattr(svc, desc.stop_method, None)
        if callable(stop_method) and stop_method is not shutdown_method:
            setattr(
                svc,
                desc.stop_method,
                _counting(stop_calls, name, stop_method),
            )

    container.start()
    container.shutdown()

    for name in shutdown_calls:
        assert shutdown_calls[name] == 1, (
            f"MANAGED service '{name}' shutdown called {shutdown_calls[name]} times"
        )
    for name in stop_calls:
        assert stop_calls[name] == 1, (
            f"MANAGED service '{name}' stop called {stop_calls[name]} times"
        )
    assert shutdown_calls or stop_calls, (
        "No MANAGED shutdown/stop method was recorded during teardown"
    )
