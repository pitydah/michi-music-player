from __future__ import annotations

from michi_ai.v2.core.models import (
    PermissionLevel, ToolDefinition, ErrorCode,
)
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


def test_handler_returning_none_is_not_success():
    registry = ToolRegistryV2()
    registry.register(ToolDefinition(
        name="returns_none", description="",
        handler=lambda **kw: None,
        permission=PermissionLevel.READ_ONLY,
    ))
    result = registry.execute("returns_none", {})
    assert result.ok is False
    assert result.code == ErrorCode.TOOL_FAILED


def test_handler_returning_dict_with_ok_false():
    registry = ToolRegistryV2()
    registry.register(ToolDefinition(
        name="fails", description="",
        handler=lambda **kw: {"ok": False, "error": "something went wrong"},
        permission=PermissionLevel.READ_ONLY,
    ))
    result = registry.execute("fails", {})
    assert result.ok is False
    assert "something went wrong" in result.error


def test_handler_returning_empty_dict_is_ambiguous():
    registry = ToolRegistryV2()
    registry.register(ToolDefinition(
        name="empty", description="",
        handler=lambda **kw: {},
        permission=PermissionLevel.READ_ONLY,
    ))
    result = registry.execute("empty", {})
    assert result.ok is True


def test_gateway_returning_none_is_not_ok():
    from michi_ai.v2.tools.register_builtin import _make_handler
    handler = _make_handler(None, "test_method")
    result = handler()
    assert result["ok"] is False
    assert "CAPABILITY_UNAVAILABLE" in str(result.get("code", ""))


def test_no_false_success_on_missing_handler():
    registry = ToolRegistryV2()
    registry.register(ToolDefinition(
        name="no_handler", description="",
        permission=PermissionLevel.READ_ONLY,
    ))
    result = registry.execute("no_handler", {})
    assert result.ok is False
    assert result.code == ErrorCode.TOOL_UNAVAILABLE
