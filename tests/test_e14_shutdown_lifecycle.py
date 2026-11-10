"""M4: shutdown must settle queued completions while Qt can still dispatch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from michi_ecosystem.composition import (
    EcosystemBusyError,
    EcosystemRuntime,
    ShutdownPhase,
)


def _runtime(owner: str) -> EcosystemRuntime:
    factory_busy = owner == "factory"
    account_busy = owner == "account"
    assistant_busy = owner == "home-assistant"
    operations_busy = owner == "spaces"
    home_busy = owner == "home"
    return EcosystemRuntime(
        ecosystem_bridge=SimpleNamespace(),
        factory=SimpleNamespace(bridge=SimpleNamespace(busy=factory_busy)),
        device_registry=SimpleNamespace(),
        stream_management=SimpleNamespace(),
        stream_bridge=SimpleNamespace(busy=False),
        account_bridge=SimpleNamespace(busy=account_busy),
        home_assistant_bridge=SimpleNamespace(busy=assistant_busy),
        operations_bridge=SimpleNamespace(busy=operations_busy),
        home=SimpleNamespace(busy=home_busy, close=lambda: None),
    )


@pytest.mark.parametrize(
    "owner",
    ["factory", "account", "spaces", "home", "home-assistant"],
)
def test_close_pumps_the_dispatcher_until_each_busy_owner_settles(owner: str) -> None:
    runtime = _runtime(owner)
    pumped: list[int] = []
    cancelled: list[bool] = []

    def process_pending() -> None:
        pumped.append(len(pumped))
        assert runtime.lifecycle.accepting_operations is False
        if len(pumped) >= 2:
            runtime.factory.bridge.busy = False
            runtime.account_bridge.busy = False
            runtime.operations_bridge.busy = False
            runtime.home.busy = False
            runtime.home_assistant_bridge.busy = False

    runtime.close(
        timeout=1.0,
        process_pending=process_pending,
        cancel_operations=lambda: cancelled.append(True),
    )

    assert runtime.lifecycle.phase is ShutdownPhase.CLOSED
    assert runtime.lifecycle.closed is True
    assert len(pumped) >= 2
    assert cancelled == [True]


@pytest.mark.parametrize(
    ("owner", "code"),
    [
        ("factory", "FACTORY_BUSY"),
        ("account", "ACCOUNT_BUSY"),
        ("spaces", "SPACES_BUSY"),
        ("home", "HOME_BUSY"),
        ("home-assistant", "HOME_ASSISTANT_BUSY"),
    ],
)
def test_close_timeout_reports_each_busy_owner_without_destroying_resources(
    owner: str, code: str
) -> None:
    runtime = _runtime(owner)
    with pytest.raises(EcosystemBusyError, match=code):
        runtime.close(timeout=0.05, process_pending=lambda: None)

    # The wait expired: the runtime is quiescing, not closed, and a retry is
    # still possible once the owner settles.
    assert runtime.lifecycle.phase is ShutdownPhase.QUIESCING
    assert runtime.lifecycle.closed is False
    assert runtime.lifecycle.accepting_operations is False

    runtime.factory.bridge.busy = False
    runtime.account_bridge.busy = False
    runtime.operations_bridge.busy = False
    runtime.home.busy = False
    runtime.home_assistant_bridge.busy = False
    runtime.close()
    assert runtime.lifecycle.phase is ShutdownPhase.CLOSED


def test_close_without_a_dispatcher_keeps_the_immediate_busy_refusal() -> None:
    runtime = _runtime("factory")

    with pytest.raises(EcosystemBusyError, match="FACTORY_BUSY"):
        runtime.close()

    assert runtime.lifecycle.closed is False
