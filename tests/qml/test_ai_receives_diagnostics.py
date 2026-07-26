from __future__ import annotations
from unittest.mock import MagicMock


from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


class TestReceivesDiagnostics:
    def test_michi_ai_can_accept_michi_ai_service(self):
        svc = MagicMock()
        bridge = MichiAIBridge(michi_ai_service=svc)
        assert bridge._ai_svc is svc

    def test_michi_ai_initial_state(self):
        bridge = MichiAIBridge()
        assert bridge.status == "IDLE"
        assert bridge.lastError == ""

    def test_send_message_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "FAILED"

    def test_refresh_does_not_crash(self):
        bridge = MichiAIBridge()
        bridge.refresh()

    def test_cancel_works(self):
        bridge = MichiAIBridge()
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_chat_history_works(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("hola")
        history = bridge.getChatHistory()
        assert isinstance(history, str)

    def test_ai_score_returns_dict(self):
        bridge = MichiAIBridge()
        score = bridge.aiScore()
        assert "score" in score
        assert "has_ai_service" in score

    def test_suggestions_after_refresh(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert len(bridge.suggestions) > 0
