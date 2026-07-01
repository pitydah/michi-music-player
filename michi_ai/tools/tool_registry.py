"""ToolRegistry — register, list, and execute Michi AI tools.

Each tool is a callable with a name, description, permission level,
and optional confirmation requirement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from michi_ai.tools.tool_permissions import ToolPermission, permission_requires_confirmation
from michi_ai.tools.tool_result import ToolResult

logger = logging.getLogger("michi_ai.tool_registry")


@dataclass
class ToolDef:
    name: str
    description: str
    permission: str = ToolPermission.READ_ONLY
    requires_confirmation: bool = False
    fn: Callable | None = None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        if tool.requires_confirmation is False and permission_requires_confirmation(tool.permission):
            tool.requires_confirmation = True
        self._tools[tool.name] = tool
        logger.debug("Tool registered: %s (perm=%s confirm=%s)", tool.name, tool.permission, tool.requires_confirmation)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "permission": t.permission, "requires_confirmation": t.requires_confirmation}
            for t in self._tools.values()
        ]

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def execute(self, name: str, params: dict | None = None, confirmed: bool = False) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, code="NOT_FOUND", message=f"Tool '{name}' not found.")
        if tool.requires_confirmation and not confirmed:
            return ToolResult(ok=False, code="CONFIRMATION_REQUIRED", message=f"Tool '{name}' requiere confirmacion.", requires_confirmation=True)
        if tool.fn is None:
            return ToolResult(ok=False, code="NO_IMPLEMENTATION", message=f"Tool '{name}' no tiene implementacion.")
        try:
            result = tool.fn(**(params or {}))
            if isinstance(result, ToolResult):
                return result
            return ToolResult(ok=True, code="OK", message="Ejecutado.", data={"result": result})
        except Exception as e:
            logger.exception("Tool '%s' failed", name)
            return ToolResult(ok=False, code="ERROR", message=str(e))
