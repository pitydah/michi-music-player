from __future__ import annotations
from unittest.mock import MagicMock


from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


class TestSettingsKeys:
    def test_bridge_instantiates_with_michi_ai_service(self):
        svc = MagicMock()
        bridge = MichiAIBridge(michi_ai_service=svc)
        assert bridge._ai_svc is svc

    def test_initial_status_idle(self):
        bridge = MichiAIBridge()
        assert bridge.status == "IDLE"

    def test_send_message_cancel(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"

    def test_chat_history_appends_user_message(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("hola")
        assert bridge._chat_history[0]["role"] == "user"

    def test_chat_history_has_assistant_response(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("hola")
        assert bridge._chat_history[-1]["role"] == "assistant"
