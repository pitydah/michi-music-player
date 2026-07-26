from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def services() -> None:
    svc = {
        "michi_ai_service": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
    }
    svc["michi_ai_service"].process_message.return_value = {"ok": True, "response": "Hecho."}
    return svc


@pytest.fixture
def bridge(services) -> None:
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
    )


class TestMichiAIConversation:
    def test_user_message_in_history(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["role"] == "user"
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_assistant_response_in_history(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Hecho."
        }
        bridge.sendMessage("reproduce canción 7")
        assert len(bridge._chat_history) >= 2
        assert bridge._chat_history[-1]["role"] == "assistant"
        assert "Hecho" in bridge._chat_history[-1]["text"]

    def test_unknown_message_gets_fallback_from_engine(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No entendí esa solicitud."
        }
        bridge.sendMessage("xyzzy unrecognized")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "No entendí" in last["text"]

    def test_chat_history_serializes_to_json(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Playlist creada."
        }
        bridge.sendMessage("crear playlist llamada Test")
        history = bridge.getChatHistory()
        parsed = json.loads(history)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1
        assert parsed[0]["role"] == "user"

    def test_multiple_messages_chained(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "OK"
        }
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2
        bridge.sendMessage("reproduce canción 2")
        assert len(bridge._chat_history) >= 4

    def test_assistant_response_for_confirmation(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "Confirmas" in last["text"]

    def test_confirmed_action_shows_result(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Playlist creada."},
        ]
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_rejected_action_shows_cancelled(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Acción cancelada."},
        ]
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        assert bridge._pending_action is not None
        bridge.sendMessage("no")
        assert bridge.status in ("SUCCEEDED", "FAILED", "CANCELLED")

    def test_chat_history_no_duplicate_replay(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 1")
        count = sum(
            1 for m in bridge._chat_history
            if m.get("role") == "user" and "reproduce canción" in m.get("text", "")
        )
        assert count == 1

    def test_no_pending_confirmation_gives_feedback(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "No hay acción pendiente."
        }
        bridge.sendMessage("sí")
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"

    def test_cancel_without_pending(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Cancelado."
        }
        bridge.sendMessage("no")
        assert bridge.status == "SUCCEEDED"

    def test_chat_history_empty_initial(self, bridge) -> None:
        assert bridge._chat_history == []

    def test_chat_history_clears_on_pending_action(self, bridge) -> None:
        assert bridge._pending_action is None
