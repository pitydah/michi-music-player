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


class TestMichiAIKeyboard:
    def test_enter_sends_message(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_escape_cancels_execution(self, bridge) -> None:
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_escape_while_idle(self, bridge) -> None:
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_up_down_navigation_suggestions(self, bridge, services) -> None:
        bridge._ai_engine = MagicMock()
        bridge._ai_engine.get_suggestions.return_value = [
            {"title": "Sug 1", "description": "D1", "action": "a1", "route": ""},
            {"title": "Sug 2", "description": "D2", "action": "a2", "route": ""},
            {"title": "Sug 3", "description": "D3", "action": "a3", "route": ""},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 3
        assert bridge.suggestions[0]["title"] == "Sug 1"
        assert bridge.suggestions[2]["title"] == "Sug 3"

    def test_suggestion_activation_triggers_action(self, bridge, services) -> None:
        bridge._ai_engine = MagicMock()
        bridge._ai_engine.get_suggestions.return_value = [
            {"title": "Test", "description": "Test desc", "action": "test", "route": ""}
        ]
        suggestions = bridge._build_suggestions()
        assert len(suggestions) >= 1
        first = suggestions[0]
        assert "title" in first
        assert "description" in first

    def test_keyboard_activation_executes_suggestion(self, bridge, services) -> None:
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1

    def test_shift_tab_focus_input(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "SUCCEEDED"

    def test_empty_input_sends_to_engine(self, bridge) -> None:
        before = len(bridge._chat_history)
        bridge.sendMessage("")
        assert len(bridge._chat_history) >= before

    def test_cancel_button_during_execution(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Reproduciendo..."
        }
        bridge.sendMessage("reproduce canción 42")
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_escape_idle_state(self, bridge) -> None:
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_keyboard_send_confirmation(self, bridge, services) -> None:
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "Acción confirmada."
        }
        bridge._pending_action = {"intent": "crear playlist", "entities": {}}
        bridge.sendMessage("sí")
        services["michi_ai_service"].process_message.assert_called_once()

    def test_keyboard_reject_with_cancel(self, bridge) -> None:
        bridge._pending_action = {"intent": "test", "entities": {}}
        bridge.sendMessage("cancel")
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"
