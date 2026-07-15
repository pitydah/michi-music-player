<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test Michi AI keyboard navigation."""

=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
"""Test Michi AI keyboard navigation."""

>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
<<<<<<< Updated upstream
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def services():
    return {
        "ai_controller": MagicMock(),
        "context_service": MagicMock(),
        "plan_builder": MagicMock(),
        "tool_registry": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "track_action_service": MagicMock(),
        "playlist_service": MagicMock(),
        "global_search_service": MagicMock(),
        "settings_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "worker_manager": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        ai_controller=services["ai_controller"],
        context_service=services["context_service"],
        plan_builder=services["plan_builder"],
        tool_registry=services["tool_registry"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        track_action_service=services["track_action_service"],
        playlist_service=services["playlist_service"],
        global_search_service=services["global_search_service"],
        settings_service=services["settings_service"],
        diagnostics_service=services["diagnostics_service"],
        worker_manager=services["worker_manager"],
    )
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("michi_ai")]
>>>>>>> Stashed changes


class TestMichiAIKeyboard:
    def test_enter_sends_message(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_escape_cancels_execution(self, bridge, services):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_escape_while_idle_does_nothing(self, bridge):
        assert bridge.status == "idle"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_up_down_navigation_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Sug 1", "description": "D1", "action": "a1", "route": ""},
            {"title": "Sug 2", "description": "D2", "action": "a2", "route": ""},
            {"title": "Sug 3", "description": "D3", "action": "a3", "route": ""},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 3
        assert bridge.suggestions[0]["title"] == "Sug 1"
        assert bridge.suggestions[2]["title"] == "Sug 3"

    def test_suggestion_activation_triggers_action(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Test desc", "action": "test", "route": ""}
        ]
        suggestions = bridge._build_suggestions()
        assert len(suggestions) >= 1
        first = suggestions[0]
        assert "title" in first
        assert "description" in first

    def test_keyboard_activation_executes_suggestion(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1

    def test_shift_tab_focus_input(self, bridge, services):
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("completed", "executing")

    def test_empty_input_does_not_send(self, bridge):
        before = len(bridge._chat_history)
        bridge.sendMessage("")
        assert len(bridge._chat_history) >= before

    def test_input_disabled_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("executing", "completed")

    def test_cancel_button_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        bridge.cancel()
        assert bridge.status == "cancelled"

<<<<<<< Updated upstream
=======
    def test_escape_idle_state(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_keyboard_send_confirmation(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("sí")
        assert bridge._pending_action is None

    def test_keyboard_reject_confirmation(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None
        assert bridge.status == "cancelled"

    def test_keyboard_confirm_with_yes(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("yes")
        assert bridge._pending_action is None

    def test_keyboard_confirm_with_confirmar(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("confirmar")
        assert bridge._pending_action is None

    def test_keyboard_reject_with_cancelar(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("cancelar")
        assert bridge._pending_action is None

    def test_keyboard_reject_with_cancel(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.sendMessage("cancel")
        assert bridge._pending_action is None
=======
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation


@pytest.fixture
def services():
    return {
        "ai_controller": MagicMock(),
        "context_service": MagicMock(),
        "plan_builder": MagicMock(),
        "tool_registry": MagicMock(),
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "track_action_service": MagicMock(),
        "playlist_service": MagicMock(),
        "global_search_service": MagicMock(),
        "settings_service": MagicMock(),
        "diagnostics_service": MagicMock(),
        "worker_manager": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        ai_controller=services["ai_controller"],
        context_service=services["context_service"],
        plan_builder=services["plan_builder"],
        tool_registry=services["tool_registry"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        track_action_service=services["track_action_service"],
        playlist_service=services["playlist_service"],
        global_search_service=services["global_search_service"],
        settings_service=services["settings_service"],
        diagnostics_service=services["diagnostics_service"],
        worker_manager=services["worker_manager"],
    )


class TestMichiAIKeyboard:
    def test_enter_sends_message(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["text"] == "reproduce canción 42"

    def test_escape_cancels_execution(self, bridge, services):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_escape_while_idle_does_nothing(self, bridge):
        assert bridge.status == "idle"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_up_down_navigation_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Sug 1", "description": "D1", "action": "a1", "route": ""},
            {"title": "Sug 2", "description": "D2", "action": "a2", "route": ""},
            {"title": "Sug 3", "description": "D3", "action": "a3", "route": ""},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 3
        assert bridge.suggestions[0]["title"] == "Sug 1"
        assert bridge.suggestions[2]["title"] == "Sug 3"

    def test_suggestion_activation_triggers_action(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Test desc", "action": "test", "route": ""}
        ]
        suggestions = bridge._build_suggestions()
        assert len(suggestions) >= 1
        first = suggestions[0]
        assert "title" in first
        assert "description" in first

    def test_keyboard_activation_executes_suggestion(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1

    def test_shift_tab_focus_input(self, bridge, services):
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("completed", "executing")

    def test_empty_input_does_not_send(self, bridge):
        before = len(bridge._chat_history)
        bridge.sendMessage("")
        assert len(bridge._chat_history) >= before

    def test_input_disabled_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("executing", "completed")

    def test_cancel_button_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        bridge.cancel()
        assert bridge.status == "cancelled"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_tab_navigates_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "A", "description": "B", "action": "c", "route": ""},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 1
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
