"""Michi AI Config Tools — configuration plans."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def list_config_plans(planner=None, **kwargs) -> ToolResult:
    if planner is None:
        return ToolResult(ok=True, data={"plans": []})
    try:
        plans = planner.list_plan_types() if hasattr(planner, "list_plan_types") else []
        return ToolResult(ok=True, data={"plans": plans})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def create_config_plan(planner=None, plan_type: str = "", context: dict | None = None, **kwargs) -> ToolResult:
    if planner is None:
        return ToolResult(ok=False, code="NO_PLANNER", message="ConfigPlanner no disponible.")
    if not plan_type:
        return ToolResult(ok=False, code="NO_TYPE", message="Tipo de plan no especificado.")
    try:
        plan = planner.create_plan(plan_type, context)
        return ToolResult(ok=True, data={"plan_id": plan.plan_id, "title": plan.title, "description": plan.description}, requires_confirmation=True)
    except ValueError as e:
        return ToolResult(ok=False, code="INVALID_TYPE", message=str(e))
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))
