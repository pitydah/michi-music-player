# -*- coding: utf-8 -*-
"""Test for ApplicationBootstrap."""

from unittest.mock import MagicMock

from core.application_bootstrap import ApplicationBootstrap
from core.service_container import ContainerState


def test_create():
    svc = ApplicationBootstrap()
    assert svc is not None


def test_build():
    svc = ApplicationBootstrap()
    result = svc.build()
    assert result is not None
    assert result is svc


def test_start_restores_once_before_bridge_creation():
    bootstrap = ApplicationBootstrap()
    bootstrap._has_built = True
    events = []
    queue = MagicMock()
    queue.restore.side_effect = lambda: events.append("restore") or {"ok": True}
    settings = MagicMock()
    settings.value.return_value = True
    bootstrap.container.register("queue_service", queue)
    bootstrap.container.register("settings_manager", settings)
    bootstrap.container.start = lambda: setattr(
        bootstrap.container, "_state", ContainerState.READY
    )
    bootstrap.create_bridges = lambda: events.append("bridges") or {}

    bootstrap.run()
    bootstrap.start()

    assert events == ["restore", "bridges"]
    queue.restore.assert_called_once_with()


def test_start_does_not_restore_when_session_memory_is_disabled():
    bootstrap = ApplicationBootstrap()
    bootstrap._has_built = True
    queue = MagicMock()
    settings = MagicMock()
    settings.value.return_value = False
    bootstrap.container.register("queue_service", queue)
    bootstrap.container.register("settings_manager", settings)
    bootstrap.container.start = lambda: setattr(
        bootstrap.container, "_state", ContainerState.READY
    )

    bootstrap.start()

    queue.restore.assert_not_called()
