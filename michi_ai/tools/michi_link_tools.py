"""Michi AI Michi Link Tools — Micro Server discovery and connection."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def get_michi_link_status(michi_link_ctrl=None, **kwargs) -> ToolResult:
    if michi_link_ctrl is None:
        return ToolResult(ok=True, data={"available": False})
    try:
        state = michi_link_ctrl.get_connection_state() if hasattr(michi_link_ctrl, "get_connection_state") else {}
        return ToolResult(ok=True, data={"available": True, "state": state})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def discover_micro_server(host: str = "", port: int = 53318, micro_server_service=None, **kwargs) -> ToolResult:
    if micro_server_service is None:
        return ToolResult(ok=False, code="NO_SERVICE", message="MicroServerService no disponible.")
    if not host:
        return ToolResult(ok=False, code="NO_HOST", message="Host no especificado.")
    try:
        result = micro_server_service.discover(host, port)
        ok = getattr(result, "ok", False)
        return ToolResult(ok=ok, data={"host": host, "port": port, "discovered": ok})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))
