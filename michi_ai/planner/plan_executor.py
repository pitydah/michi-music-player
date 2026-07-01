"""PlanExecutor — validate, confirm, and execute ActionPlans via ToolRegistry."""

from __future__ import annotations

import logging
from typing import Any

from michi_ai.planner.action_plan import ActionPlan
from michi_ai.tools.tool_registry import ToolRegistry
from michi_ai.tools.tool_result import ToolResult

logger = logging.getLogger("michi_ai.plan_executor")


class PlanExecutor:
    def __init__(self, tool_registry: ToolRegistry):
        self._tools = tool_registry

    def preview(self, plan: ActionPlan) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "title": plan.title,
            "description": plan.description,
            "steps": [{"tool": s.tool, "description": s.description} for s in plan.steps],
            "risks": plan.risks,
            "tests": plan.tests,
        }

    def execute(self, plan: ActionPlan, confirmed: bool = False) -> ToolResult:
        if not confirmed and plan.requires_confirmation:
            return ToolResult(ok=False, code="CONFIRMATION_REQUIRED", message=f"Plan '{plan.title}' requiere confirmacion.", requires_confirmation=True)
        results = []
        for step in plan.steps:
            result = self._tools.execute(step.tool, step.params, confirmed=True)
            results.append({"tool": step.tool, "ok": result.ok, "message": result.message})
            if not result.ok:
                logger.warning("Plan step '%s' failed: %s", step.tool, result.message)
                return ToolResult(ok=False, code="STEP_FAILED", message=f"Paso '{step.tool}' fallo: {result.message}", data={"results": results})
        return ToolResult(ok=True, code="PLAN_COMPLETED", message=f"Plan '{plan.title}' completado.", data={"results": results})
