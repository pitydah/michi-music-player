from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge, AI_STATES
from ui_qml_bridge.action_registry import ActionRegistry

pytestmark = [pytest.mark.qml_module("michi_ai")]


@pytest.fixture
def ai_service():
    svc = MagicMock()
    svc.process_message.return_value = {"ok": True, "response": "Hecho."}
    svc.get_suggestions.return_value = []
    return svc


@pytest.fixture
def registry():
    r = ActionRegistry()
    for aid in (
        "track_play_now", "track_add_to_queue", "playlist_create",
        "track_add_to_playlist", "diagnostics_show", "navigate_settings",
        "navigate_home", "navigate_library", "library_scan", "metadata_edit",
    ):
        act = r.get(aid)
        if act:
            act.handler = lambda: {"ok": True}
            act.enabled = True
    return r


@pytest.fixture
def bridge(ai_service, registry):
    return MichiAIBridge(
        michi_ai_service=ai_service,
        action_registry=registry,
        navigation_bridge=MagicMock(),
        job_service=MagicMock(),
        confirmation_service=MagicMock(),
    )


class TestAICompletoFlow:
    def test_initial_state_idle(self, bridge):
        assert bridge.status == "IDLE"
        assert bridge._chat_history == []
        assert bridge._pending_action is None

    def test_status_is_valid_ai_state(self, bridge):
        assert bridge.status in AI_STATES

    def test_send_message_unknown_intent(self, bridge, ai_service):
        ai_service.process_message.side_effect = RuntimeError("unknown")
        bridge.sendMessage("zzz unknown gibberish")
        assert bridge.status == "FAILED"

    def test_play_track_goes_to_succeeded(self, bridge, ai_service):
        ai_service.process_message.return_value = {"ok": True, "response": "playing track", "executed": True}
        bridge.sendMessage("reproduce cancion 42")
        assert bridge.status == "SUCCEEDED"

    def test_search_sends_navigation(self, bridge, ai_service):
        ai_service.process_message.return_value = {"ok": True, "response": "searching..."}
        bridge.sendMessage("buscar rock progresivo")
        assert bridge.status == "SUCCEEDED"

    def test_open_route_navigates(self, bridge, ai_service):
        ai_service.process_message.return_value = {"ok": True, "response": "navigating..."}
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_create_playlist_needs_confirmation(self, bridge, ai_service):
        ai_service.process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": {"name": "playlist", "description": "create playlist"},
            "plan": {}, "entities": {}, "executed": False,
        }
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_reject_playlist_creation(self, bridge, ai_service):
        ai_service.process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": {"name": "playlist", "description": "create playlist"},
            "plan": {}, "entities": {}, "executed": False,
        }
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.cancel()
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_suggestions_fallback(self, bridge):
        bridge.refresh()
        assert len(bridge.suggestions) >= 3

    def test_suggestions_from_service(self, ai_service, registry):
        ai_service.get_suggestions.return_value = [{"title": "Test", "description": "Desc", "action": "test", "route": ""}]
        b = MichiAIBridge(michi_ai_service=ai_service, action_registry=registry)
        b.refresh()
        assert len(b.suggestions) == 1

    def test_get_chat_history_json(self, bridge, ai_service):
        ai_service.process_message.return_value = {"ok": True, "response": "playing"}
        bridge.sendMessage("reproduce cancion 1")
        import json
        history = json.loads(bridge.getChatHistory())
        assert len(history) >= 1

    def test_ai_score_returns_dict(self, bridge):
        score = bridge.aiScore()
        assert isinstance(score, dict)
        assert "score" in score
        assert "status" in score

    def test_ai_score_with_full_services(self, bridge):
        score = bridge.aiScore()
        assert score["has_ai_service"]
        assert score["has_registry"]
        assert score["score"] > 0

    def test_play_with_no_service_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("reproduce cancion 1")
        assert b.status == "FAILED"
        assert b.lastError == "NO_AI_SERVICE"

    def test_context_changed_signal(self, bridge, ai_service, qtbot):
        with qtbot.waitSignal(bridge.contextChanged, timeout=500):
            ai_service.process_message.return_value = {"ok": True, "response": "ok"}
            bridge.sendMessage("test")

    def test_plans_with_capabilities(self, bridge, ai_service):
        ai_service.process_message.assert_not_called()
        bridge.sendMessage("play")
        ai_service.process_message.assert_called_once()
        call_kwargs = ai_service.process_message.call_args[1]
        assert "context" in call_kwargs
