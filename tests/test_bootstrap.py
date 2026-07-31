# -*- coding: utf-8 -*-
"""Tests for ApplicationBootstrap explicit state machine (Parche 3).

Lifecycle: created -> initializing -> ready | degraded | failed
                                              -> shutting_down -> stopped
"""
from unittest.mock import MagicMock

import pytest

from core.application_bootstrap import (
    BOOT_CREATED,
    BOOT_DEGRADED,
    BOOT_FAILED,
    BOOT_INITIALIZING,
    BOOT_READY,
    BOOT_SHUTTING_DOWN,
    BOOT_STATES,
    BOOT_STOPPED,
    ApplicationBootstrap,
)
from core.service_container import ContainerState


def _ready_start(bootstrap: ApplicationBootstrap) -> None:
    """Patch container.start to set state READY without running real startup."""
    bootstrap.container.start = lambda: setattr(
        bootstrap.container, "_state", ContainerState.READY
    )


def _start_to(bootstrap: ApplicationBootstrap, state: ContainerState) -> None:
    bootstrap.container.start = lambda: setattr(
        bootstrap.container, "_state", state
    )


@pytest.fixture
def stub_builders(monkeypatch):
    """Replace composition builders with no-ops so build() is unit-testable."""
    from core.composition import (
        audio_lab,
        ecosystem,
        infrastructure,
        intelligence,
        library,
        playback,
        settings,
    )
    import core.navigation_service as nav_mod

    for mod in (
        infrastructure,
        playback,
        library,
        audio_lab,
        ecosystem,
        settings,
        intelligence,
    ):
        monkeypatch.setattr(mod, "build", lambda container: None)
    monkeypatch.setattr(nav_mod, "NavigationService", lambda: MagicMock())


class TestBootstrapStates:
    def test_initial_state_is_created(self):
        bootstrap = ApplicationBootstrap()
        assert bootstrap.boot_state == BOOT_CREATED
        assert bootstrap.failed_services == {}
        assert bootstrap.degraded_services == {}

    def test_all_states_are_distinct(self):
        states = [
            BOOT_CREATED,
            BOOT_INITIALIZING,
            BOOT_READY,
            BOOT_DEGRADED,
            BOOT_FAILED,
            BOOT_SHUTTING_DOWN,
            BOOT_STOPPED,
        ]
        assert len(states) == len(set(states))  # all distinct
        assert all(s in BOOT_STATES for s in states)
        assert len(BOOT_STATES) == 7

    def test_build_transitions_to_initializing(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        assert bootstrap.boot_state == BOOT_INITIALIZING
        assert bootstrap._has_built is True

    def test_build_is_idempotent(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        first = bootstrap.boot_state
        bootstrap.build()  # no-op
        assert bootstrap.boot_state == first

    def test_start_reaches_ready(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        _ready_start(bootstrap)
        bootstrap.start()
        assert bootstrap.boot_state == BOOT_READY
        assert bootstrap._has_started is True
        assert bootstrap.failed_services == {}
        assert bootstrap.degraded_services == {}

    def test_required_failure_sets_failed_state(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.container._failures["playback_service"] = "missing"
        _start_to(bootstrap, ContainerState.FAILED)
        bootstrap.start()
        assert bootstrap.boot_state == BOOT_FAILED
        assert "playback_service" in bootstrap.failed_services
        assert bootstrap.degraded_services == {}
        assert bootstrap._has_started is False

    def test_optional_failure_sets_degraded_state(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.container._failures["radio_service"] = "no radio configured"
        _start_to(bootstrap, ContainerState.DEGRADED)
        bootstrap.start()
        assert bootstrap.boot_state == BOOT_DEGRADED
        assert "radio_service" in bootstrap.degraded_services
        assert bootstrap.failed_services == {}
        assert bootstrap._has_started is True  # degraded is still runnable

    def test_container_failed_without_failures_still_failed(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        _start_to(bootstrap, ContainerState.FAILED)
        bootstrap.start()
        assert bootstrap.boot_state == BOOT_FAILED


class TestLoadQmlGuard:
    def test_load_qml_refused_when_failed(self):
        bootstrap = ApplicationBootstrap()
        bootstrap._boot_state = BOOT_FAILED
        bootstrap._failed_services["playback_service"] = "missing"
        engine = MagicMock()
        assert bootstrap.load_qml(engine) is False
        engine.load.assert_not_called()

    def test_load_qml_proceeds_when_ready(self):
        bootstrap = ApplicationBootstrap()
        bootstrap._boot_state = BOOT_READY
        engine = MagicMock()
        engine.rootObjects.return_value = [MagicMock()]
        result = bootstrap.load_qml(engine, qml_path="/tmp/Main.qml")
        assert result is True
        engine.load.assert_called_once()


class TestCreateBridgesGuard:
    def test_create_bridges_refused_when_failed(self):
        bootstrap = ApplicationBootstrap()
        bootstrap._boot_state = BOOT_FAILED
        bootstrap._failed_services["playback_service"] = "missing"
        bridges = bootstrap.create_bridges()
        assert bridges == {}

    def test_create_bridges_aborts_before_factory_when_failed(self, monkeypatch):
        bootstrap = ApplicationBootstrap()
        bootstrap._boot_state = BOOT_FAILED
        bootstrap._failed_services["playback_service"] = "missing"

        def _fail(*_args, **_kwargs):
            raise AssertionError("bridge factory must not run when BOOT_FAILED")

        monkeypatch.setattr(
            "ui_qml_bridge.bridge_factory.create_all_bridges", _fail
        )
        assert bootstrap.create_bridges() == {}


class TestShutdown:
    def test_shutdown_transitions_through_shutting_down_to_stopped(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        seen = []

        def fake_shutdown():
            seen.append(bootstrap.boot_state)

        bootstrap.container.shutdown = fake_shutdown
        bootstrap.shutdown()
        assert seen == [BOOT_SHUTTING_DOWN]
        assert bootstrap.boot_state == BOOT_STOPPED
        assert bootstrap._has_built is False

    def test_shutdown_is_idempotent(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        calls = []
        bootstrap.container.shutdown = lambda: calls.append(1)
        bootstrap.shutdown()
        bootstrap.shutdown()
        bootstrap.shutdown()
        assert calls == [1]
        assert bootstrap.boot_state == BOOT_STOPPED

    def test_shutdown_after_failed_state(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.container._failures["playback_service"] = "missing"
        _start_to(bootstrap, ContainerState.FAILED)
        bootstrap.start()
        assert bootstrap.boot_state == BOOT_FAILED
        bootstrap.shutdown()
        assert bootstrap.boot_state == BOOT_STOPPED


class TestBootReport:
    def test_report_reflects_degraded_state(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.container._failures["radio_service"] = "no radio"
        _start_to(bootstrap, ContainerState.DEGRADED)
        bootstrap.start()
        report = bootstrap.boot_report()
        assert report["state"] == BOOT_DEGRADED
        assert report["container_state"] == "degraded"
        assert report["has_started"] is True
        assert "radio_service" in report["degraded_services"]
        assert report["failed_services"] == {}

    def test_report_reflects_failed_state(self, stub_builders):
        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.container._failures["playback_service"] = "boom"
        _start_to(bootstrap, ContainerState.FAILED)
        bootstrap.start()
        report = bootstrap.boot_report()
        assert report["state"] == BOOT_FAILED
        assert "playback_service" in report["failed_services"]
        assert report["has_started"] is False
