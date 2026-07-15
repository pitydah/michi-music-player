from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAINegative:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        return MichiAIBridge(
            ai_controller=None,
            context_service=None,
            plan_builder=None,
            tool_registry=None,
            action_registry=MagicMock(),
            navigation_bridge=None,
            track_action_service=None,
            playlist_service=None,
            global_search_service=None,
            settings_service=None,
            diagnostics_service=None,
            worker_manager=None,
        )

    def test_null_bridge_does_not_crash(self, bridge):
        assert bridge.status == "idle"

    def test_null_bridge_send_message_no_crash(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert bridge.status in ("idle", "failed")

    def test_null_bridge_cancel_no_crash(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_null_bridge_refresh_no_crash(self, bridge):
        bridge.refresh()
        assert bridge.status == "idle"

    def test_null_bridge_suggestions_fallback(self, bridge):
        bridge.refresh()
        assert len(bridge.suggestions) == 5

    def test_null_bridge_ai_score(self, bridge):
        score = bridge.aiScore()
        assert score["score"] < 30

    def test_null_bridge_last_error_empty(self, bridge):
        assert bridge.lastError == ""

    def test_null_bridge_chat_history_preserved(self, bridge):
        bridge.sendMessage("test")
        assert len(bridge._chat_history) > 0

    def test_bridge_with_only_navigation(self, bridge):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        nav = MagicMock()
        b2 = MichiAIBridge(navigation_bridge=nav)
        b2.sendMessage("ir a biblioteca")
        nav.navigate.assert_called_once()

    def test_bridge_no_services_play_fails(self, bridge):
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "failed"
        assert bridge.lastError != ""

    def test_bridge_no_services_search_fails(self, bridge):
        bridge.sendMessage("buscar rock")
        assert bridge.status == "failed"

    def test_bridge_no_services_enqueue_fails(self, bridge):
        bridge.sendMessage("encolar canción 5")
        assert bridge.status == "failed"

    def test_bridge_no_services_create_playlist(self, bridge):
        bridge.sendMessage("crear playlist test")
        assert bridge.status == "awaiting_confirmation"

    def test_bridge_invalid_status_ignored(self, bridge):
        bridge._set_status("invalid_status")
        assert bridge.status != "invalid_status"

    def test_bridge_unknown_intent_returns_fallback(self, bridge):
        bridge.sendMessage("zxcvbnm")
        assert any("No entendí" in m.get("text", "") for m in bridge._chat_history if m.get("role") == "assistant")
