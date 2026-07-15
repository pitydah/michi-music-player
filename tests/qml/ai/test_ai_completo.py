from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge, AI_STATES
from ui_qml_bridge.action_registry import ActionRegistry

pytestmark = [pytest.mark.qml_module("michi_ai")]


@pytest.fixture
def registry():
    r = ActionRegistry()
    for aid, handler_fn in (
        ("track_play_now", lambda: {"ok": True}),
        ("track_add_to_queue", lambda: {"ok": True}),
        ("playlist_create", lambda: {"ok": True, "id": 1}),
        ("track_add_to_playlist", lambda: {"ok": True}),
        ("diagnostics_show", lambda: {"ok": True}),
        ("navigate_settings", lambda: {"ok": True}),
        ("navigate_home", lambda: {"ok": True}),
        ("navigate_library", lambda: {"ok": True}),
        ("library_scan", lambda: {"ok": True}),
        ("metadata_edit", lambda: {"ok": True}),
    ):
        act = r.get(aid)
        if act:
            act.handler = handler_fn
            act.enabled = True
    return r


@pytest.fixture
def services():
    return {
        "device_sync_service": MagicMock(),
        "job_service": MagicMock(),
        "confirmation_service": MagicMock(),
        "navigation_bridge": MagicMock(),
        "capability_bridge": MagicMock(),
        "page_state_store": MagicMock(),
        "accessibility_bridge": MagicMock(),
    }


@pytest.fixture
def bridge(services, registry):
    return MichiAIBridge(
        device_sync_service=services["device_sync_service"],
        job_service=services["job_service"],
        action_registry=registry,
        confirmation_service=services["confirmation_service"],
        navigation_bridge=services["navigation_bridge"],
        capability_bridge=services["capability_bridge"],
        page_state_store=services["page_state_store"],
        accessibility_bridge=services["accessibility_bridge"],
    )


class TestAICompletoFlow:
    def test_initial_state_idle(self, bridge):
        assert bridge.status == "IDLE"
        assert bridge._chat_history == []
        assert bridge._pending_action is None

    def test_status_is_valid_ai_state(self, bridge):
        assert bridge.status in AI_STATES

    def test_send_message_unknown_intent(self, bridge):
        bridge.sendMessage("zzz unknown gibberish")
        assert bridge.status == "FAILED"
        last = bridge._chat_history[-1]
        assert "No entendi" in last["text"]

    def test_play_track_goes_to_succeeded(self, bridge):
        bridge.sendMessage("reproduce cancion 42")
        assert bridge.status == "SUCCEEDED"

    def test_play_album_goes_to_succeeded(self, bridge):
        bridge.sendMessage("reproduce album Dark Side")
        assert bridge.status == "SUCCEEDED"

    def test_enqueue_goes_to_succeeded(self, bridge):
        bridge.sendMessage("encolar cancion 7")
        assert bridge.status == "SUCCEEDED"

    def test_search_sends_navigation(self, bridge):
        bridge.sendMessage("buscar rock progresivo")
        assert bridge.status == "SUCCEEDED"

    def test_open_route_navigates(self, bridge):
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "SUCCEEDED"

    def test_create_playlist_needs_confirmation(self, bridge):
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"

    def test_confirm_playlist_creation(self, bridge):
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("si")
        assert bridge.status in ("SUCCEEDED", "RUNNING")

    def test_reject_playlist_creation(self, bridge):
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "CONFIRMATION_REQUIRED"
        bridge.sendMessage("no")
        assert bridge.status == "CANCELLED"
        assert bridge._pending_action is None

    def test_destroy_action_cancel(self, bridge):
        bridge.sendMessage("no")
        assert bridge.status == "CANCELLED"

    def test_suggestions_fallback(self, bridge):
        bridge.refresh()
        assert len(bridge.suggestions) == 5

    def test_suggestions_from_service(self, services, registry):
        svc = MagicMock()
        svc.get_suggestions.return_value = [{"title": "Test", "description": "Desc", "action": "test", "route": ""}]
        b = MichiAIBridge(confirmation_service=svc, action_registry=registry)
        b.refresh()
        assert len(b.suggestions) == 1

    def test_get_chat_history_json(self, bridge):
        bridge.sendMessage("reproduce cancion 1")
        hist = bridge.getChatHistory()
        import json
        parsed = json.loads(hist)
        assert len(parsed) >= 1
        assert parsed[0]["role"] == "user"

    def test_conversation_multiple_turns(self, bridge):
        bridge.sendMessage("reproduce cancion 1")
        c1 = len(bridge._chat_history)
        bridge.sendMessage("reproduce cancion 2")
        c2 = len(bridge._chat_history)
        assert c2 > c1

    def test_ai_score_basic(self, bridge):
        score = bridge.aiScore()
        assert "score" in score
        assert score["status"] == "IDLE"

    def test_ai_score_after_message(self, bridge):
        bridge.sendMessage("reproduce cancion 1")
        score = bridge.aiScore()
        assert score["chat_count"] >= 1
        assert score["status"] == "SUCCEEDED"

    def test_cancel_clears_pending_action(self, bridge):
        bridge._pending_action = {"name": "test", "description": "test"}
        bridge.cancel()
        assert bridge._pending_action is None
        assert bridge.status == "CANCELLED"

    def test_send_message_adds_user_turn(self, bridge):
        bridge.sendMessage("hola")
        assert bridge._chat_history[0]["role"] == "user"
        assert bridge._chat_history[0]["text"] == "hola"

    def test_assistant_response_after_play(self, bridge):
        bridge.sendMessage("reproduce cancion 1")
        last = bridge._chat_history[-1]
        assert last["role"] == "assistant"
        assert "Hecho" in last["text"]

    def test_partial_success_not_available_in_simple_flow(self, bridge):
        bridge._set_status("PARTIAL_SUCCESS")
        assert bridge.status == "PARTIAL_SUCCESS"
