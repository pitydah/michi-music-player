"""Test Michi AI conversation display and history."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def services():
    return {
        "ai_controller": MagicMock(),
        "context_service": MagicMock(),
        "plan_builder": MagicMock(),
        "tool_registry": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "track_action_service": MagicMock(),
        "playlist_service": MagicMock(),
        "global_search_service": MagicMock(),
        "settings_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "worker_manager": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        ai_controller=services["ai_controller"],
        context_service=services["context_service"],
        plan_builder=services["plan_builder"],
        tool_registry=services["tool_registry"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        track_action_service=services["track_action_service"],
        playlist_service=services["playlist_service"],
        global_search_service=services["global_search_service"],
        settings_service=services["settings_service"],
        diagnostics_service=services["diagnostics_service"],
        worker_manager=services["worker_manager"],
    )


class TestMichiAIConversation:
    def test_user_message_in_history(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["role"] == "user"
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_assistant_response_in_history(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 7")
        assert len(bridge._chat_history) >= 2
        assert bridge._chat_history[-1]["role"] == "assistant"
        assert "Hecho" in bridge._chat_history[-1]["text"]

    def test_unknown_message_gets_fallback_response(self, bridge):
        bridge.sendMessage("xyzzy unrecognized")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "No entendí" in last["text"]

    def test_chat_history_serializes_to_json(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Test")
        history = bridge.getChatHistory()
        parsed = json.loads(history)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1
        assert parsed[0]["role"] == "user"

    def test_multiple_messages_chained(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2
        bridge.sendMessage("reproduce canción 2")
        assert len(bridge._chat_history) >= 4

    def test_assistant_response_for_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "Confirmas" in last["text"] or "confirma" in last["text"].lower()

    def test_confirmed_action_shows_result(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "executing")

    def test_rejected_action_shows_cancelled(self, bridge):
        bridge._pending_action = {"name": "test", "description": "test action"}
        bridge.sendMessage("no")
        assert bridge.status == "cancelled"
        last = bridge._chat_history[-1]
        assert "cancelada" in last["text"].lower()

    def test_no_pending_confirmation_gives_feedback(self, bridge):
        bridge.sendMessage("sí")
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "no hay" in last["text"].lower() or "No hay" in last["text"]

    def test_confirm_without_pending_does_not_execute(self, bridge):
        before = len(bridge._chat_history)
        bridge.sendMessage("sí")
        assert len(bridge._chat_history) == before + 2

    def test_cancel_without_pending(self, bridge):
        bridge.sendMessage("no")
        assert bridge.status == "cancelled"

    def test_chat_history_empty_initial(self, bridge):
        assert bridge._chat_history == []

    def test_chat_history_clears_on_cancel(self, bridge):
        bridge.sendMessage("no")
        assert bridge._pending_action is None
