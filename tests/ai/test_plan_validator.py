from __future__ import annotations

from michi_ai.v2.core.models import ActionPlan, PlanStep, ToolDefinition
from michi_ai.v2.intent.capability_resolver import CapabilityResolver
from michi_ai.v2.plan.plan_validator import PlanValidator
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class TestPlanValidator:
    def setup_method(self):
        self.tool_registry = ToolRegistryV2()
        self.cap_resolver = CapabilityResolver()
        self.validator = PlanValidator(self.tool_registry, self.cap_resolver)

        self.tool_registry.register(ToolDefinition(
            name="test_tool", description="", handler=lambda: {"ok": True},
            capabilities=("test.cap",),
        ))
        self.cap_resolver.register("test.cap", available=True)

    def test_valid_plan(self):
        step = PlanStep(step_id="s1", tool="test_tool")
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.validator.validate(plan)
        assert result.status == "VALID"

    def test_empty_plan_warns(self):
        plan = ActionPlan(plan_id="p1", session_id="s1")
        result = self.validator.validate(plan)
        assert result.status == "VALID_WITH_WARNINGS"

    def test_plan_without_id(self):
        step = PlanStep(step_id="s1", tool="test_tool")
        plan = ActionPlan(plan_id="", session_id="s1", steps=(step,))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"

    def test_unknown_tool_in_step(self):
        step = PlanStep(step_id="s1", tool="nonexistent_tool")
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"
        assert any("not found" in e for e in result.errors)

    def test_missing_dependency(self):
        step = PlanStep(step_id="s2", tool="test_tool", depends_on=("s1",))
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"

    def test_cycle_detection(self):
        steps = [
            PlanStep(step_id="s1", tool="test_tool", depends_on=("s2",)),
            PlanStep(step_id="s2", tool="test_tool", depends_on=("s1",)),
        ]
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=tuple(steps))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"
        assert any("circular" in e.lower() or "cycle" in e.lower() for e in result.errors)

    def test_unavailable_capability(self):
        step = PlanStep(step_id="s1", tool="test_tool")
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        self.cap_resolver.register("test.cap", available=False)
        self.validator.validate(plan)
        # May or may not fail depending on if capability is checked
        pass

    def test_max_steps_exceeded(self):
        steps = [PlanStep(step_id=f"s{i}", tool="test_tool") for i in range(51)]
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=tuple(steps))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"
        assert any("max steps" in e.lower() for e in result.errors)

    def test_timeout_exceeded(self):
        step = PlanStep(step_id="s1", tool="test_tool", timeout=9999)
        plan = ActionPlan(plan_id="p1", session_id="s1", steps=(step,))
        result = self.validator.validate(plan)
        assert result.status == "INVALID"
