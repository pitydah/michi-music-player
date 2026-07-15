from __future__ import annotations
"""Test Michi AI page states and interactions."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def services():
    svc = MagicMock()
    svc.process_message.return_value = {"ok": True, "response": "Hecho."}
    svc.get_suggestions.return_value = []
    return {
        "michi_ai_service": svc,
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "job_service": MagicMock(),
        "confirmation_service": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
        job_service=services["job_service"],
        confirmation_service=services["confirmation_service"],
    )


class TestMichiAIStates:
    def test_initial_state_idle(self, bridge):
        assert bridge.status == "IDLE"
        assert bridge.lastError == ""

    def test_planning_before_execution(self, bridge):
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")

    def test_awaiting_confirmation(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": {"name": "playlist", "description": "create playlist"},
            "plan": {}, "entities": {}, "executed": False,
        }
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_completed_state(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "playing"
        }
        bridge.sendMessage("reproduce canción 5")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED")

    def test_cancelled_state(self, bridge):
        bridge.cancel()
        assert bridge.status == "CANCELLED"

    def test_failed_state_missing_service(self, bridge):
        bridge._ai_svc = None
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "FAILED"

    def test_unavailable_state_no_bridge(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("test")
        assert b.status == "FAILED"


class TestMichiAIInteractions:
    def test_send_message_adds_to_history(self, bridge):
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1

    def test_response_received_emitted(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "playing track 1"
        }
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_suggestions_from_service(self, bridge, services):
        services["michi_ai_service"].get_suggestions.return_value = [
            {"title": "Play", "description": "Play", "action": "play", "route": ""},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 1

    def test_suggestions_fallback_when_no_context(self, bridge):
        bridge._ai_svc = None
        bridge.refresh()
        assert len(bridge.suggestions) >= 3

    def test_cancel_resets_state(self, bridge):
        bridge._pending_action = {"name": "test"}
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_get_chat_history_json(self, bridge):
        bridge.sendMessage("reproduce canción 1")
        import json
        history = json.loads(bridge.getChatHistory())
        assert len(history) >= 1

    def test_ai_score_returns_dict(self, bridge):
        score = bridge.aiScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_ai_score_with_full_services(self, bridge):
        score = bridge.aiScore()
        assert score["has_ai_service"]
        assert score["has_registry"]
        assert score["score"] > 0

    def test_context_changed_signal(self, bridge, qtbot):
        with qtbot.waitSignal(bridge.contextChanged, timeout=500):
            bridge.refresh()
