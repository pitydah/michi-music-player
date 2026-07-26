from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


class TestMichiAIExecution:
    def test_send_message_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "FAILED"

    def test_cancel_works(self):
        bridge = MichiAIBridge()
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_send_message_then_cancel(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 42")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_confirm_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True, "response": "Hecho."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_reject_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": False, "response": "Error."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("no")
        assert bridge.status == "FAILED"

    def test_create_playlist_no_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "FAILED"

    def test_send_message_sets_chat(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_action_failed_result_message(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 999")
        assert bridge.status == "FAILED"
