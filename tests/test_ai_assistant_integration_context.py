"""Integration tests: AiAssistantController → AIAssistantService → ToolRegistry."""

from unittest.mock import MagicMock
from legacy_widgets.ui.controllers.legacy_controllers.ai_assistant_controller import AiAssistantController


def test_assistant_controller_builds_service_with_context(monkeypatch):
    monkeypatch.setenv("MICHI_SAFE_MODE", "0")
    ctrl = AiAssistantController(db=MagicMock(), playback=MagicMock(), safe_mode=False)
    ctx = MagicMock()
    ctrl.set_context_service(ctx)

    svc = ctrl._get_service()

    assert svc._context_svc is ctx


def test_assistant_tool_registry_ignores_extra_playback_kwargs():
    from integrations.ai_assistant.tool_registry import ToolRegistry
    from integrations.ai_assistant.schemas import ToolResult
    import integrations.ai_assistant.permissions as perms

    def sample_tool(db, query=""):
        return ToolResult(name="sample_tool", success=True, data={"query": query})

    old = perms.TOOL_PERMISSIONS.get("sample_tool")
    perms.TOOL_PERMISSIONS["sample_tool"] = perms.PermissionLevel.READ_ONLY
    try:
        reg = ToolRegistry()
        reg.register("sample_tool", sample_tool)
        result = reg.execute("sample_tool", db=MagicMock(), query="abc", playback=MagicMock())
        assert result.success
        assert result.data["query"] == "abc"
    finally:
        if old is None:
            perms.TOOL_PERMISSIONS.pop("sample_tool", None)
        else:
            perms.TOOL_PERMISSIONS["sample_tool"] = old
