from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


class TestReceivesDiagnostics:
    def test_diagnose_message_forwards_to_engine(self) -> None:
        svc = MagicMock()
        svc.process_message.return_value = {"ok": True, "response": "Diagnóstico completo."}
        bridge = MichiAIBridge(michi_ai_service=svc)
        bridge.sendMessage("diagnosticar biblioteca")
        svc.process_message.assert_called_once()
        assert bridge.status == "SUCCEEDED"

    def test_diagnose_engine_fails(self) -> None:
        svc = MagicMock()
        svc.process_message.return_value = {"ok": False, "response": "Error de diagnóstico"}
        bridge = MichiAIBridge(michi_ai_service=svc)
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "FAILED"

    def test_diagnose_no_ai_service(self) -> None:
        bridge = MichiAIBridge()
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "FAILED"
        assert bridge.lastError == "NO_AI_SERVICE"

    def test_diagnose_with_action_registry(self) -> None:
        svc = MagicMock()
        svc.process_message.return_value = {"ok": True, "response": "OK"}
        bridge = MichiAIBridge(
            michi_ai_service=svc,
            action_registry=MagicMock(),
        )
        assert bridge._registry is not None
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_diagnose_engine_exception(self) -> None:
        svc = MagicMock()
        svc.process_message.side_effect = Exception("Engine error")
        bridge = MichiAIBridge(michi_ai_service=svc)
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "FAILED"

    def test_diagnose_result_in_chat(self) -> None:
        svc = MagicMock()
        svc.process_message.return_value = {"ok": True, "response": "Todo correcto."}
        bridge = MichiAIBridge(michi_ai_service=svc)
        bridge.sendMessage("diagnosticar biblioteca")
        assert any("Todo correcto" in m.get("text", "") for m in bridge._chat_history)
