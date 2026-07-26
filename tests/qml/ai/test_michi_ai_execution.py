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
        "job_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "capability_bridge": MagicMock(),
        "page_state_store": MagicMock(),
        "accessibility_bridge": MagicMock(),
    }
    svc["michi_ai_service"].process_message.return_value = {"ok": True, "response": "OK"}
    return svc


@pytest.fixture
def bridge(services) -> None:
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        job_service=services["job_service"],
        confirmation_service=services["confirmation_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        capability_bridge=services["capability_bridge"],
        page_state_store=services["page_state_store"],
        accessibility_bridge=services["accessibility_bridge"],
    )


class TestMichiAIExecution:
    def test_send_message_calls_ai_engine(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 42")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_send_message_success_status(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "SUCCEEDED"

    def test_send_message_failed_status(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "No encontrado"
        }
        bridge.sendMessage("reproduce canción 999")
        assert bridge.status == "FAILED"

    def test_confirmation_required(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "requires_confirmation": True, "intent": "crear playlist"
        }
        bridge.sendMessage("crear playlist")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_cancel_clears_pending(self, bridge) -> None:
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_no_ai_service_returns_failed(self) -> None:
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "FAILED"
        assert bridge.lastError == "NO_AI_SERVICE"

    def test_response_in_chat_history(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        assert "Reproduciendo" in bridge._chat_history[-1]["text"]

    def test_failed_response_in_chat_history(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Canción no encontrada"
        }
        bridge.sendMessage("reproduce canción 999")
        assert len(bridge._chat_history) >= 1
        assert "no encontrada" in bridge._chat_history[-1]["text"].lower()

    def test_ai_engine_exception_sets_failed(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = Exception("Engine error")
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "FAILED"
        assert "Error" in bridge._chat_history[-1]["text"]

    def test_send_message_stores_user_message(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "OK"
        }
        bridge.sendMessage("reproduce canción 42")
        assert any(
            m["role"] == "user" and "reproduce" in m["text"]
            for m in bridge._chat_history
        )

    def test_ai_score_reflects_services(self, bridge, services) -> None:
        score = bridge.aiScore()
        assert score["has_ai_service"] is True
        assert score["has_nav"] is True
        assert score["has_registry"] is True
        assert score["score"] > 0

    def test_ai_score_minimal(self) -> None:
        bridge = MichiAIBridge()
        score = bridge.aiScore()
        assert score["has_ai_service"] is False
        assert score["score"] >= 5  # status + suggestions

    def test_get_chat_history_json(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Listo"
        }
        bridge.sendMessage("reproduce canción 1")
        history = bridge.getChatHistory()
        assert isinstance(history, str)
        assert "user" in history
        assert "assistant" in history
