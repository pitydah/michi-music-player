from __future__ import annotations


from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


class TestNoFalseSuccess:
    def test_send_message_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce Bohemian Rhapsody")
        assert bridge.status == "FAILED"
        assert bridge._last_error == "NO_AI_SERVICE"

    def test_send_message_empty_does_not_crash(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("")
        assert bridge._chat_history

    def test_send_message_cancel(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"

    def test_send_message_no_fake_success(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción XYZNotFound")
        assert bridge.status != "SUCCEEDED"

    def test_send_message_no_fake_confirmation(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("crear playlist")
        assert bridge.status != "CONFIRMATION_REQUIRED"

    def test_action_unknown_fallback(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("nonexistent command")
        assert len(bridge._chat_history) >= 2
