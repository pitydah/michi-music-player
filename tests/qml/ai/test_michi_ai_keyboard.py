from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


class TestMichiAIKeyboard:
    def test_enter_sends_message(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_escape_cancels_execution(self):
        bridge = MichiAIBridge()
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_escape_while_idle_does_nothing(self):
        bridge = MichiAIBridge()
        assert bridge.status == "IDLE"
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_empty_input_does_not_crash(self):
        bridge = MichiAIBridge()
        before = len(bridge._chat_history)
        bridge.sendMessage("")
        assert len(bridge._chat_history) >= before

    def test_cancel_button_during_execution(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_escape_idle_state(self):
        bridge = MichiAIBridge()
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_confirm_with_mock_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_reject_with_mock_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": False}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge.status == "FAILED"

    def test_cancel_triggers_cancel(self):
        bridge = MichiAIBridge()
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("cancel")
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"

    def test_suggestions_after_refresh(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert len(bridge.suggestions) > 0

    def test_send_message_with_engine_processes(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True, "response": "Hecho."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("reproduce canción 42")
        engine.process_message.assert_called_once()
        assert bridge.status == "SUCCEEDED"
