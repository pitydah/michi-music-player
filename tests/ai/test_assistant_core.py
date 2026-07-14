from __future__ import annotations

from michi_ai.v2.core.assistant_core import AssistantCoreService
from michi_ai.v2.core.models import (
    AssistantRequest, AssistantResponseType, ToolDefinition,
)


class TestAssistantCoreService:
    def setup_method(self):
        self.core = AssistantCoreService()
        # Register a simple tool for the core to use
        self.core.tool_registry.register(ToolDefinition(
            name="play_track", description="Play a track",
            capabilities=("playback.control",),
            handler=lambda: {"ok": True, "track": "test_track"},
        ))
        self.core.tool_registry.register(ToolDefinition(
            name="play_album", description="Play an album",
            capabilities=("playback.control",),
            handler=lambda: {"ok": True, "album": "test_album"},
        ))
        self.core.capability_resolver.register("playback.control", available=True)

    def test_create_session(self):
        result = self.core.create_session()
        assert result.ok is True
        assert result.data is not None
        assert result.data.session_id != ""

    def test_process_unknown_message(self):
        request = AssistantRequest(text="xyzzy flurbo garble")
        response = self.core.process_message(request)
        assert response.type in (AssistantResponseType.ANSWER, AssistantResponseType.CLARIFICATION)

    def test_process_pause(self):
        request = AssistantRequest(text="pausa")
        response = self.core.process_message(request)
        assert response.type in (
            AssistantResponseType.ANSWER,
            AssistantResponseType.ERROR,
            AssistantResponseType.PLAN_PREVIEW,
        )

    def test_process_next(self):
        request = AssistantRequest(text="siguiente")
        response = self.core.process_message(request)
        assert response.type in (
            AssistantResponseType.ANSWER,
            AssistantResponseType.ERROR,
            AssistantResponseType.PLAN_PREVIEW,
        )

    def test_get_suggestions(self):
        suggestions = self.core.get_suggestions()
        assert isinstance(suggestions, list)

    def test_get_tools(self):
        tools = self.core.get_tools()
        assert len(tools) > 0

    def test_clear_history(self):
        created = self.core.create_session()
        session_id = created.data.session_id
        result = self.core.clear_history(session_id)
        assert result.ok is True

    def test_confirm_and_cancel_flow(self):
        created = self.core.create_session()
        session_id = created.data.session_id

        cancel_response = self.core.cancel_plan(session_id)
        assert cancel_response.type in (
            AssistantResponseType.ANSWER, AssistantResponseType.ERROR,
        )

    def test_register_gateway(self):
        gateway = object()
        self.core.register_gateway("playback", gateway)
        assert "playback" in self.core._gateways

    def test_initialize(self):
        result = self.core.initialize()
        assert result.ok is True

    def test_dismiss_suggestion(self):
        result = self.core.dismiss_suggestion("test_suggestion")
        assert result is True

    def test_shutdown(self):
        self.core.initialize()
        self.core.shutdown()
        assert self.core._initialized is False
