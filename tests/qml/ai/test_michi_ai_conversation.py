from __future__ import annotations
import json
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


class TestMichiAIConversation:
    def test_user_message_in_history(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["role"] == "user"
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_assistant_response_in_history(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 7")
        assert len(bridge._chat_history) >= 2
        assert bridge._chat_history[-1]["role"] == "assistant"

    def test_unknown_message_gets_fallback_response(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("xyzzy unrecognized")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"

    def test_chat_history_serializes_to_json(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("hola")
        history = bridge.getChatHistory()
        parsed = json.loads(history)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1
        assert parsed[0]["role"] == "user"

    def test_multiple_messages_chained(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2
        bridge.sendMessage("reproduce canción 2")
        assert len(bridge._chat_history) >= 4

    def test_confirmed_action_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True, "response": "Hecho."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_rejected_action_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": False, "response": "Error."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("no")
        assert bridge.status == "FAILED"

    def test_chat_history_empty_initial(self):
        bridge = MichiAIBridge()
        assert bridge._chat_history == []

    def test_no_pending_confirmation_gives_feedback(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("sí")
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"

    def test_confirm_without_pending_does_not_execute(self):
        bridge = MichiAIBridge()
        before = len(bridge._chat_history)
        bridge.sendMessage("sí")
        assert len(bridge._chat_history) == before + 2

    def test_cancel_without_pending(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"

    def test_chat_history_no_duplicate_replay(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 1")
        count = sum(1 for m in bridge._chat_history if m.get("role") == "user" and "reproduce canción" in m.get("text", ""))
        assert count == 1
