from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = [pytest.mark.qml_module("michi_ai")]


@pytest.fixture
def services() -> None:
    svc = {
        "michi_ai_service": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
    }
    svc["michi_ai_service"].process_message.return_value = {"ok": True, "response": "OK"}
    return svc


@pytest.fixture
def bridge(services) -> None:
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
    )


class TestMichiAIWorkflow:
    def test_workflow_prompt_preview_confirm_execute(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Playlist creada."},
        ]
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_prompt_reject_cancels(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.cancel()
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"

    def test_workflow_prompt_execute_show_result(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Hecho."
        }
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "SUCCEEDED"
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"]

    def test_workflow_prompt_fails_shows_error(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Error: NOT_FOUND"
        }
        bridge.sendMessage("reproduce canción 999")
        assert bridge.status == "FAILED"
        last = bridge._chat_history[-1]
        assert "Error" in last["text"]

    def test_workflow_full_cycle(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_workflow_destructive_requires_confirm(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_workflow_confirm_then_execute(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = [
            {"requires_confirmation": True, "intent": "crear playlist"},
            {"ok": True, "response": "Playlist creada."},
        ]
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("sí")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_execute_without_confirm_skips(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_navigate_prompt(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Navegando..."
        }
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_search_prompt(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Resultados encontrados"
        }
        bridge.sendMessage("buscar jazz")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_unknown_prompt_fallback(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No entendí esa solicitud."
        }
        bridge.sendMessage("haz algo mágico")
        last = bridge._chat_history[-1]
        assert "No entendí" in last["text"]

    def test_workflow_cancel_during_execution(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 1")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_workflow_execution_progress_tracking(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 10")
        assert bridge.status == "SUCCEEDED"

    def test_workflow_partial_execution_shows_result(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Hecho."
        }
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"]
        assert bridge.status == "SUCCEEDED"
