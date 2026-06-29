"""Tool registry — safe execution of registered AI tools with permission checks."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from integrations.ai_assistant.permissions import TOOL_PERMISSIONS
from integrations.ai_assistant.schemas import PermissionLevel, ToolResult

logger = logging.getLogger("michi.ai_assistant.tool_registry")


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}

    def register(self, name: str, fn: Callable):
        self._tools[name] = fn

    def execute(self, name: str, db: Any, **kwargs) -> ToolResult:
        if name not in self._tools:
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta desconocida: {name}",
            )
        level = TOOL_PERMISSIONS.get(name)
        if level is None or level == PermissionLevel.FORBIDDEN:
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta bloqueada: {name}. Permisos insuficientes.",
                permission_denied=True,
            )
        if level == PermissionLevel.REVERSIBLE or level == PermissionLevel.RESOURCE_INTENSIVE:
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta '{name}' requiere confirmacion. "
                      "Usa execute_direct() tras la confirmacion del usuario.",
                permission_denied=True,
            )
        try:
            return self._call_tool(name, db, **kwargs)
        except Exception as e:
            logger.warning("Tool %s error: %s", name, e)
            return ToolResult(name=name, success=False, error=str(e))

    def execute_direct(self, name: str, db: Any, **kwargs) -> ToolResult:
        """Execute a REVERSIBLE or READ_ONLY tool after user confirmation.
        Blocks SENSITIVE and FORBIDDEN tools. No anonymous execution."""
        if name not in self._tools:
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta desconocida: {name}",
            )
        level = TOOL_PERMISSIONS.get(name)
        if level is None:
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta sin permiso definido: {name}",
                permission_denied=True,
            )
        if level in (PermissionLevel.SENSITIVE, PermissionLevel.FORBIDDEN):
            return ToolResult(
                name=name, success=False,
                error=f"Herramienta bloqueada: {name} (nivel {level.name}).",
                permission_denied=True,
            )
        try:
            return self._call_tool(name, db, **kwargs)
        except Exception as e:
            logger.warning("Tool %s execute_direct error: %s", name, e)
            return ToolResult(name=name, success=False, error=str(e))

    def _call_tool(self, name: str, db: Any, **kwargs) -> ToolResult:
        fn = self._tools[name]
        try:
            sig = inspect.signature(fn)
        except (ValueError, TypeError):
            sig = None

        if sig is not None:
            call_kwargs = {"db": db}
            for key, value in kwargs.items():
                if key in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    call_kwargs[key] = value
            result = fn(**call_kwargs)
        else:
            result = fn(db=db, **kwargs)

        if isinstance(result, ToolResult):
            return result
        return ToolResult(name=name, success=True, data=result)

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": name, "permission": TOOL_PERMISSIONS.get(name, None).name if TOOL_PERMISSIONS.get(name) else "UNKNOWN"}
            for name in self._tools
        ]

    @property
    def count(self) -> int:
        return len(self._tools)
