from __future__ import annotations

from michi_ai.v2.core.models import ErrorCode, ToolDefinition
from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2


class TestToolRegistryV2:
    def test_register_and_get(self):
        registry = ToolRegistryV2()
        defn = ToolDefinition(name="test_tool", description="A test tool")
        registry.register(defn)
        retrieved = registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_has_tool(self):
        registry = ToolRegistryV2()
        defn = ToolDefinition(name="exists", description="")
        registry.register(defn)
        assert registry.has_tool("exists") is True
        assert registry.has_tool("missing") is False

    def test_list_tools(self):
        registry = ToolRegistryV2()
        registry.register(ToolDefinition(name="a", description=""))
        registry.register(ToolDefinition(name="b", description=""))
        tools = registry.list_tools()
        assert len(tools) == 2

    def test_execute_unknown_tool(self):
        registry = ToolRegistryV2()
        result = registry.execute("nonexistent", {})
        assert result.ok is False
        assert result.code == ErrorCode.TOOL_NOT_FOUND

    def test_execute_no_handler(self):
        registry = ToolRegistryV2()
        defn = ToolDefinition(name="no_handler", description="No handler")
        registry.register(defn)
        result = registry.execute("no_handler", {})
        assert result.ok is False
        assert result.code == ErrorCode.TOOL_UNAVAILABLE

    def test_execute_handler_success(self):
        registry = ToolRegistryV2()

        def my_handler(arg1="default"):
            return {"ok": True, "result": arg1}

        defn = ToolDefinition(
            name="my_tool", description="My tool",
            handler=my_handler,
        )
        registry.register(defn)
        result = registry.execute("my_tool", {"arg1": "hello"})
        assert result.ok is True
        assert result.data.get("result") == "hello"

    def test_execute_handler_failure(self):
        registry = ToolRegistryV2()

        def failing_handler():
            return {"ok": False, "error": "something broke"}

        defn = ToolDefinition(name="failing", description="", handler=failing_handler)
        registry.register(defn)
        result = registry.execute("failing", {})
        assert result.ok is False

    def test_execute_handler_exception(self):
        registry = ToolRegistryV2()

        def broken_handler():
            raise ValueError("internal error")

        defn = ToolDefinition(name="broken", description="", handler=broken_handler)
        registry.register(defn)
        result = registry.execute("broken", {})
        assert result.ok is False
        assert result.code == ErrorCode.TOOL_FAILED

    def test_validate_args_missing_required(self):
        registry = ToolRegistryV2()

        def handler(required_arg):
            return {"ok": True}

        defn = ToolDefinition(
            name="required_test", description="",
            input_schema={"required": ["required_arg"], "properties": {"required_arg": {"type": "string"}}},
            handler=handler,
        )
        registry.register(defn)
        result = registry.execute("required_test", {})
        assert result.ok is False
        assert result.code == ErrorCode.INVALID_ARGUMENTS

    def test_validate_args_wrong_type(self):
        registry = ToolRegistryV2()

        def handler(count):
            return {"ok": True}

        defn = ToolDefinition(
            name="type_test", description="",
            input_schema={"required": ["count"], "properties": {"count": {"type": "integer"}}},
            handler=handler,
        )
        registry.register(defn)
        result = registry.execute("type_test", {"count": "not_an_int"})
        assert result.ok is False
        assert result.code == ErrorCode.INVALID_ARGUMENTS

    def test_execute_with_cancellation(self):
        from michi_ai.v2.core.cancellation import CancellationToken
        registry = ToolRegistryV2()

        def handler():
            return {"ok": True}

        defn = ToolDefinition(name="cancel_test", description="", handler=handler)
        registry.register(defn)
        token = CancellationToken()
        token.cancel("stopped")
        result = registry.execute("cancel_test", {}, cancellation_token=token)
        assert result.ok is False

    def test_capability_resolver_linked(self):
        registry = ToolRegistryV2()
        defn = ToolDefinition(
            name="cap_test", description="",
            capabilities=("test.cap",),
            handler=lambda: {"ok": True},
        )
        registry.register(defn)
        caps = registry.capability_resolver.resolve("test.cap")
        assert "test.cap" in caps
