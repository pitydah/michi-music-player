from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIPage:
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

    def test_bridge_has_required_signals(self, bridge):
        assert hasattr(bridge, "contextChanged")
        assert hasattr(bridge, "responseReceived")
        assert hasattr(bridge, "statusChanged")

    def test_bridge_initial_state(self, bridge):
        assert bridge.status == "idle"

    def test_bridge_status_property(self, bridge):
        assert hasattr(bridge, "status")

    def test_bridge_send_message_sets_understanding(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert bridge.status in ("understanding", "completed", "failed")

    def test_bridge_context_changed_on_refresh(self, bridge):
        signals = []
        bridge.contextChanged.connect(lambda: signals.append(True))
        bridge.refresh()
        assert len(signals) >= 1

    def test_bridge_suggestions_default_count(self, bridge):
        bridge.refresh()
        assert len(bridge.suggestions) == 5

    def test_bridge_state_init_to_idle(self, bridge):
        assert bridge._status == "idle"

    def test_bridge_cancel_clears_state(self, bridge):
        bridge._status = "executing"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_bridge_last_error_empty_on_start(self, bridge):
        assert bridge.lastError == ""

    def test_bridge_ai_score_returns_dict(self, bridge):
        score = bridge.aiScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_bridge_chat_history_after_message(self, bridge):
        bridge.sendMessage("reproduce canción")
        history = bridge.getChatHistory()
        assert len(history) > 0

    def test_bridge_status_valid_on_execute(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert bridge.status in ("idle", "understanding", "planning", "awaiting_confirmation", "executing", "completed", "cancelled", "failed")
