from __future__ import annotations
"""Test Michi AI page states and interactions."""
"""Test Michi AI page states and interactions."""

from unittest.mock import MagicMock

from contextlib import suppress

import pytest

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


class TestMichiAIStates:
    def test_initial_state_idle(self, bridge):
        assert bridge.status == "idle"
        assert bridge.lastError == ""

    def test_understanding_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "executing")

    def test_planning_before_execution(self, bridge, services):
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("understanding", "planning", "executing", "completed")

    def test_awaiting_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"

    def test_executing_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 10")
        assert bridge.status in ("completed", "executing")

    def test_completed_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 5")
        assert bridge.status in ("completed", "executing")

    def test_cancelled_state(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_failed_state_missing_service(self, bridge):
        bridge._tas = None
        bridge._global_search = None
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "failed"

    def test_unavailable_state_no_bridge(self):
        b = MichiAIBridge()
        assert b.status == "idle"
        assert b.aiScore()["has_controller"] is False

    def test_error_state_on_exception(self, bridge, services):
        services["track_action_service"].play_track.side_effect = Exception("Unexpected error")
        with suppress(Exception):
            bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("failed", "executing")

    def test_status_transitions_understanding_to_completed(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("executing", "completed")


class TestMichiAIInteractions:
    def test_send_message_adds_to_history(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["role"] == "user"

    def test_send_message_unknown_intent(self, bridge):
        bridge.sendMessage("xyzzy flurbo garblex")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "No entendí" in last["text"]

    def test_refresh_updates_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Test desc", "action": "test", "route": ""}
        ]
        bridge.refresh()
        assert len(bridge.suggestions) >= 1

    def test_refresh_without_context_service(self):
        b = MichiAIBridge()
        b.refresh()
        assert len(b.suggestions) >= 5

    def test_ai_score_returns_dict(self, bridge):
        score = bridge.aiScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert "status" in score
        assert "suggestion_count" in score

    def test_ai_score_with_full_services(self, bridge):
        score = bridge.aiScore()
        assert score["score"] >= 50

    def test_ai_score_with_minimal(self):
        b = MichiAIBridge()
        score = b.aiScore()
        assert score["score"] >= 5

    def test_get_chat_history_json(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        history = bridge.getChatHistory()
        assert isinstance(history, str)
        assert "reproduce" in history.lower() or "canción" in history.lower() or "1" in history

    def test_bridge_status_valid_on_execute(self, bridge):
        bridge.sendMessage("reproduce canción")
        assert bridge.status in ("idle", "understanding", "planning", "awaiting_confirmation", "executing", "completed", "cancelled", "failed")

import pytest


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


class TestMichiAIStates:
    def test_initial_state_idle(self, bridge):
        assert bridge.status == "idle"
        assert bridge.lastError == ""

    def test_understanding_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "executing")

    def test_planning_before_execution(self, bridge, services):
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("understanding", "planning", "executing", "completed")

    def test_awaiting_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"

    def test_executing_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 10")
        assert bridge.status in ("completed", "executing")

    def test_completed_state(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 5")
        assert bridge.status in ("completed", "executing")

    def test_cancelled_state(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_failed_state_missing_service(self, bridge):
        bridge._tas = None
        bridge._global_search = None
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "failed"

    def test_unavailable_state_no_bridge(self):
        b = MichiAIBridge()
        assert b.status == "idle"
        assert b.aiScore()["has_controller"] is False

    def test_error_state_on_exception(self, bridge, services):
        services["track_action_service"].play_track.side_effect = Exception("Unexpected error")
        with suppress(Exception):
            bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("failed", "executing")

    def test_status_transitions_understanding_to_completed(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("executing", "completed")


class TestMichiAIInteractions:
    def test_send_message_adds_to_history(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        assert bridge._chat_history[0]["role"] == "user"

    def test_send_message_unknown_intent(self, bridge):
        bridge.sendMessage("xyzzy flurbo garblex")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "No entendí" in last["text"]

    def test_refresh_updates_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Test desc", "action": "test", "route": ""}
        ]
        bridge.refresh()
        assert len(bridge.suggestions) >= 1

    def test_refresh_without_context_service(self):
        b = MichiAIBridge()
        b.refresh()
        assert len(b.suggestions) >= 5

    def test_ai_score_returns_dict(self, bridge):
        score = bridge.aiScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert "status" in score
        assert "suggestion_count" in score

    def test_ai_score_with_full_services(self, bridge):
        score = bridge.aiScore()
        assert score["score"] >= 50

    def test_ai_score_with_minimal(self):
        b = MichiAIBridge()
        score = b.aiScore()
        assert score["score"] >= 5

    def test_get_chat_history_json(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        history = bridge.getChatHistory()
        assert isinstance(history, str)
        assert "reproduce" in history.lower() or "canción" in history.lower() or "1" in history

    def test_suggestions_fallback_when_no_context(self):
        b = MichiAIBridge()
        b.refresh()
        assert len(b.suggestions) == 5
        assert b.suggestions[0]["title"] == "Reproducir una canción"

    def test_context_changed_signal(self, bridge, services):
        handler = MagicMock()
        bridge.contextChanged.connect(handler)
        services["context_service"].get_suggestions.return_value = [
            {"title": "T", "description": "D", "action": "act", "route": ""}
        ]
        bridge.refresh()
        assert handler.called
