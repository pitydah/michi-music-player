from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIConversation:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        return MichiAIBridge(
            ai_controller=MagicMock(),
            context_service=MagicMock(),
            plan_builder=MagicMock(),
            tool_registry=MagicMock(),
            action_registry=MagicMock(),
            navigation_bridge=MagicMock(),
            track_action_service=MagicMock(),
            playlist_service=MagicMock(),
            global_search_service=MagicMock(),
            settings_service=MagicMock(),
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
        )

    def test_chat_history_appends_user_message(self, bridge):
        bridge.sendMessage("hola michy")
        assert any(m.get("role") == "user" for m in bridge._chat_history)

    def test_chat_history_appends_assistant_response(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert any(m.get("role") == "assistant" for m in bridge._chat_history)

    def test_chat_history_preserves_multiple_messages(self, bridge):
        bridge.sendMessage("buscar rock")
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_chat_history_getter_returns_json(self, bridge):
        bridge.sendMessage("hola")
        history = bridge.getChatHistory()
        assert isinstance(history, str)
        assert "user" in history or "assistant" in history

    def test_chat_history_user_text_preserved(self, bridge):
        bridge.sendMessage("reproduce canción 42")
        assert any("42" in m.get("text", "") for m in bridge._chat_history if m.get("role") == "user")

    def test_chat_history_empty_initially(self, bridge):
        assert len(bridge._chat_history) == 0

    def test_chat_history_after_cancel(self, bridge):
        bridge.sendMessage("cancelar")
        assert any(m.get("role") == "assistant" for m in bridge._chat_history)

    def test_chat_history_after_confirmation(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("sí")
        assert any(m.get("role") == "assistant" for m in bridge._chat_history)

    def test_chat_history_after_rejection(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("no")
        assert any("cancelada" in m.get("text", "").lower() for m in bridge._chat_history if m.get("role") == "assistant")

    def test_chat_history_no_duplicate_replay(self, bridge):
        bridge.sendMessage("reproduce canción 1")
        count = sum(1 for m in bridge._chat_history if m.get("role") == "user" and "reproduce canción" in m.get("text", ""))
        assert count == 1
