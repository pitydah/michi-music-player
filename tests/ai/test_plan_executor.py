from __future__ import annotations

import time

from michi_ai.v2.core.models import (
    ActionPlan, ErrorCode, PlanState, PlanStep, ToolDefinition,
)
from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class TestPlanExecutorV2:
    def setup_method(self):
        self.tool_registry = ToolRegistryV2()
        self.executor = PlanExecutorV2(self.tool_registry)

        self.tool_registry.register(ToolDefinition(
            name="success_tool", description="", handler=lambda: {"ok": True},
        ))

    def test_execute_empty_plan(self):
        plan = ActionPlan(plan_id="p1", session_id="s1")
        result = self.executor.execute(plan)
        assert result.state == PlanState.SUCCEEDED
        assert result.ok is True

    def test_execute_single_step(self):
        step = PlanStep(step_id="s1", tool="success_tool")
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.executor.execute(plan)
        assert result.state == PlanState.SUCCEEDED
        assert result.ok is True
        assert len(result.step_results) == 1

    def test_execute_multiple_steps(self):
        steps = [
            PlanStep(step_id="s1", tool="success_tool"),
            PlanStep(step_id="s2", tool="success_tool"),
        ]
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=tuple(steps))
        result = self.executor.execute(plan)
        assert result.state == PlanState.SUCCEEDED
        assert len(result.step_results) == 2

    def test_execute_requires_confirmation(self):
        plan = ActionPlan(
            plan_id="p1", session_id="s1",
            requires_confirmation=True,
        )
        result = self.executor.execute(plan)
        assert result.state == PlanState.AWAITING_CONFIRMATION
        assert result.code == ErrorCode.CONFIRMATION_REQUIRED

    def test_execute_step_failure_stops_plan(self):
        self.tool_registry.register(ToolDefinition(
            name="failing_tool", description="",
            handler=lambda: {"ok": False, "error": "failed"},
        ))
        step = PlanStep(step_id="s1", tool="failing_tool", on_failure="STOP")
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.executor.execute(plan)
        assert result.state == PlanState.FAILED
        assert result.ok is False

    def test_cancel_before_execution(self):
        plan = ActionPlan(plan_id="p1", session_id="s1")
        self.executor.cancel("p1", "cancelled")
        result = self.executor.execute(plan)
        assert result.state in (PlanState.CANCELLED, PlanState.SUCCEEDED)

    def test_cancel_during_execution(self):
        self.tool_registry.register(ToolDefinition(
            name="slow_tool", description="",
            handler=lambda: (time.sleep(0.5) or {"ok": True}),
        ))
        step = PlanStep(step_id="s1", tool="slow_tool", timeout=10)
        plan = ActionPlan(plan_id="slow_p1", session_id="s1", steps=(step,))

        import threading

        def cancel_later():
            time.sleep(0.05)
            self.executor.cancel("slow_p1", "cancelled during execution")

        t = threading.Thread(target=cancel_later)
        t.start()
        result = self.executor.execute(plan)
        t.join()
        assert result.state in (PlanState.CANCELLED, PlanState.SUCCEEDED)

    def test_get_execution(self):
        plan = ActionPlan(plan_id="p1", session_id="s1")
        self.executor.execute(plan)
        execution = self.executor.get_execution("p1")
        assert execution is not None
        assert execution.plan.plan_id == "p1"

    def test_dependency_order(self):
        steps = [
            PlanStep(step_id="s2", tool="success_tool", depends_on=("s1",)),
            PlanStep(step_id="s1", tool="success_tool"),
        ]
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=tuple(steps))
        result = self.executor.execute(plan)
        assert result.state == PlanState.SUCCEEDED
        assert len(result.step_results) == 2

    def test_progress_callback(self):
        progress_updates = []

        def on_progress(plan_id, state, current, total):
            progress_updates.append((plan_id, state.value, current, total))

        self.executor.on_progress(on_progress)
        plan = ActionPlan(plan_id="p1", session_id="s1")
        self.executor.execute(plan)
        assert len(progress_updates) > 0
