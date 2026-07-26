from __future__ import annotations
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


class TestMichiAIWorkflow:
    def test_workflow_prompt_fails_without_engine(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "FAILED"

    def test_workflow_prompt_reject_cancels(self):
        bridge = MichiAIBridge()
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("cancel")
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"

    def test_workflow_confirm_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": True, "response": "Hecho."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_reject_with_engine(self):
        engine = MagicMock()
        engine.process_message.return_value = {"ok": False, "response": "Error."}
        bridge = MichiAIBridge(michi_ai_service=engine)
        bridge.sendMessage("no")
        assert bridge.status == "FAILED"

    def test_workflow_unknown_prompt_fallback(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("haz algo mágico")
        assert len(bridge._chat_history) >= 2

    def test_workflow_cancel_during_execution(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 1")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_workflow_full_cycle(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_workflow_refresh_does_not_crash(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert bridge is not None

    def test_workflow_suggestions_after_refresh(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert len(bridge.suggestions) > 0
