from __future__ import annotations

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


class TestNoFalseSuccess:
    def test_no_ai_service_returns_failed(self) -> None:
        bridge = MichiAIBridge()
        bridge.sendMessage("reproduce Bohemian Rhapsody")
        assert bridge.status == "FAILED"
        assert bridge.lastError == "NO_AI_SERVICE"

    def test_engine_search_fails(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "SEARCH_FAILED"
        }
        bridge.sendMessage("reproduce Nothing Else Matters")
        assert bridge.status == "FAILED"

    def test_engine_not_found(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "TRACK_NOT_FOUND"
        }
        bridge.sendMessage("reproduce canción XYZNotFound")
        assert bridge.status == "FAILED"

    def test_enqueue_fails(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "TRACK_NOT_FOUND"
        }
        bridge.sendMessage("encolar canción Inexistente")
        assert bridge.status == "FAILED"

    def test_open_settings_no_nav(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "NO_NAV"
        }
        bridge.sendMessage("abrir ajustes")
        assert bridge.status == "FAILED"

    def test_diagnose_no_diagnostics(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "NO_DIAGNOSTICS"
        }
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "FAILED"

    def test_action_unknown(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "UNKNOWN_ACTION"
        }
        bridge.sendMessage("nonexistent")
        assert bridge.status == "FAILED"

    def test_no_fake_ok_true_from_play_when_engine_fails(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "TRACK_NOT_FOUND"
        }
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "FAILED"
        assert bridge.lastError != ""

    def test_no_fake_ok_true_from_play_album_when_engine_fails(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "ALBUM_NOT_FOUND"
        }
        bridge.sendMessage("reproduce el álbum Test")
        assert bridge.status == "FAILED"

    def test_no_fake_encolado_simulado(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "TRACK_NOT_FOUND"
        }
        bridge.sendMessage("encolar canción Unknown")
        assert bridge.status == "FAILED"
        chat = bridge.getChatHistory()
        assert "simulado" not in chat.lower()

    def test_conversation_history_on_failure(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "response": "Error occurred"
        }
        bridge.sendMessage("reproduce canción 999")
        assert len(bridge._chat_history) >= 2
        assert bridge._chat_history[-1]["role"] == "assistant"

    def test_engine_exception_not_swallowed(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.side_effect = Exception("Engine crash")
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "FAILED"
        assert "Error" in bridge._chat_history[-1]["text"]

    def test_cancel_returns_cancelled(self, bridge) -> None:
        bridge.sendMessage("cancel")
        assert bridge.status == "CANCELLED"
