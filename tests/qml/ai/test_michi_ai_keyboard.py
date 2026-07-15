from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIKeyboard:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        return MichiAIBridge(
            ai_controller=MagicMock(),
            context_service=MagicMock(),
            plan_builder=MagicMock(),
            tool_registry=MagicMock(),
            action_registry=MagicMock(),
            navigation_bridge=MagicMock(),
            track_action_service=MagicMock(),
            playlist_service=MagicMock(),
            global_search_service=MagicMock(),
            settings_service=MagicMock(),
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
        )

    def test_enter_sends_message(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert len(bridge._chat_history) > 0

    def test_enter_with_empty_text_does_nothing(self, bridge):
        bridge.sendMessage("")
        assert bridge._status == "idle"

    def test_enter_with_whitespace_does_nothing(self, bridge):
        bridge.sendMessage("   ")
        assert bridge.status != "understanding"

    def test_escape_clears_pending(self, bridge):
        bridge._pending_action = {"name": "crear playlist"}
        bridge.cancel()
        assert bridge._pending_action is None

    def test_escape_during_execution(self, bridge):
        bridge._status = "executing"
        bridge._current_task_id = "task_1"
        bridge.cancel()
        assert bridge.status == "cancelled"

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
