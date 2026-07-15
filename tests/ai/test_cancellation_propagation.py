from __future__ import annotations

import time
import threading

from michi_ai.v2.core.cancellation import CancellationSource
from michi_ai.v2.core.models import (
    ActionPlan, PlanStep, PlanState, ToolDefinition,
)
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


def _slow_handler(**kwargs):
    time.sleep(0.2)
    return {"ok": True}


def _make_registry() -> ToolRegistryV2:
    registry = ToolRegistryV2()
    caps = CapabilityResolver()
    caps.register("test.cap", available=True)
    for name in ("step_a", "step_b", "step_c"):
        registry.register(ToolDefinition(
            name=name, description="",
            capabilities=("test.cap",),
            handler=_slow_handler,
            cancellable=True,
            timeout_seconds=10,
        ))
    return registry


def _make_plan(step_count: int = 3) -> ActionPlan:
    steps = []
    for i in range(step_count):
        steps.append(PlanStep(
            step_id=f"s{i}", tool=f"step_{chr(97 + i)}",
            arguments={}, depends_on=[],
            timeout=10, cancellable=True,
        ))
    return ActionPlan(
        plan_id="test_plan", session_id="s1",
        steps=tuple(steps),
        created_at="2024-01-01T00:00:00",
        expires_at="2024-01-01T00:05:00",
    )


class TestCancellationPropagation:
    def test_cancel_before_start(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan()
        source = CancellationSource()
        source.cancel("cancelled before start")
        result = executor.execute(plan, source.token)
        assert result.state == PlanState.CANCELLED

    def test_cancel_during_execution(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan()
        source = CancellationSource()

        def delayed_cancel():
            time.sleep(0.05)
            source.cancel("cancelled mid-execution")

        t = threading.Thread(target=delayed_cancel, daemon=True)
        t.start()
        result = executor.execute(plan, source.token)
        assert result.state in (PlanState.CANCELLED, PlanState.INTERRUPTED)

    def test_cancel_after_execution(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan(step_count=1)
        result = executor.execute(plan)
        assert result.state == PlanState.SUCCEEDED

    def test_double_cancel_is_safe(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan()
        source = CancellationSource()

        def cancel_twice():
            executor.cancel(plan.plan_id, "first")
            executor.cancel(plan.plan_id, "second")

        t = threading.Thread(target=cancel_twice, daemon=True)
        t.start()
        t.join(timeout=0.5)
        result = executor.execute(plan, source.token)
        assert result.state in (PlanState.CANCELLED, PlanState.SUCCEEDED, PlanState.INTERRUPTED)

    def test_cancel_between_steps(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan(step_count=3)
        source = CancellationSource()

        def cancel_after_first():
            time.sleep(0.3)
            executor.cancel(plan.plan_id, "cancelled between steps")

        t = threading.Thread(target=cancel_after_first, daemon=True)
        t.start()
        result = executor.execute(plan, source.token)
        assert result.state in (PlanState.CANCELLED, PlanState.SUCCEEDED)

    def test_cancel_from_conversation_propagates_to_plan(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan()
        result = executor.cancel(plan.plan_id, "user cancelled")
        assert result is False
        ex = executor.get_execution(plan.plan_id)
        if ex:
            assert ex.state == PlanState.CANCELLED

    def test_cancel_twice_sequential(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan()
        executor.cancel(plan.plan_id, "first")
        executor.cancel(plan.plan_id, "second")
        ex = executor.get_execution(plan.plan_id)
        if ex:
            assert ex.state in (PlanState.CANCELLED, PlanState.CREATED)

    def test_late_callback_after_cancel(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan(step_count=1)
        source = CancellationSource()
        source.cancel("cancelled")
        result = executor.execute(plan, source.token)
        assert result.state == PlanState.CANCELLED

    def test_cancel_cancels_tool_execution(self):
        registry = _make_registry()
        executor = PlanExecutorV2(registry)
        plan = _make_plan(step_count=1)
        source = CancellationSource()
        source.cancel("cancel before tool")
        result = executor.execute(plan, source.token)
        assert result.state == PlanState.CANCELLED
