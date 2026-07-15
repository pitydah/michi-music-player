from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAINegative:
    def test_missing_service_play_track_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("reproduce canción 42")
        assert b.status == "FAILED"

    def test_missing_navigation_service(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("ir a biblioteca")
        assert b.status == "FAILED"

    def test_missing_search_service(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("buscar rock")
        assert b.status == "FAILED"

    def test_execution_failure_propagates_error(self):
        svc = MagicMock()
        svc.process_message.return_value = {"ok": False, "error": "NO_SERVICE", "executed": False, "response": "error"}
        b = MichiAIBridge(michi_ai_service=svc)
        b.sendMessage("reproduce canción 42")
        assert b.status == "FAILED"
        assert len(b._chat_history) >= 1
        assert b._chat_history[-1]["role"] == "assistant"

    def test_cancellation_clears_pending(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.cancel()
        assert b._pending_action is None
        assert b.status == "CANCELLED"

    def test_destructive_action_requires_confirmation(self):
        svc = MagicMock()
        svc.process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": {"name": "delete", "description": "delete track"},
            "plan": {}, "entities": {}, "executed": False,
        }
        b = MichiAIBridge(michi_ai_service=svc)
        b.sendMessage("eliminar canción 42")
        assert b.status == "CONFIRMATION_REQUIRED"

    def test_unavailable_action_returns_error(self):
        svc = MagicMock()
        svc.process_message.return_value = {
            "ok": False, "error": "ACTION_UNAVAILABLE", "executed": False, "response": "not available",
        }
        b = MichiAIBridge(michi_ai_service=svc)
        b.sendMessage("hacer algo")
        assert b.status == "FAILED"

    def test_play_with_no_track_id_fails(self):
        svc = MagicMock()
        svc.process_message.return_value = {
            "ok": False, "error": "NO_TRACK_ID", "executed": False, "response": "no track id",
        }
        b = MichiAIBridge(michi_ai_service=svc)
        b.sendMessage("reproduce canción ")
        assert b.status == "FAILED"

    def test_enqueue_with_no_service_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("encolar canción 1")
        assert b.status == "FAILED"

    def test_search_with_empty_query_fails(self):
        svc = MagicMock()
        svc.process_message.return_value = {
            "ok": False, "error": "EMPTY_QUERY", "executed": False, "response": "no query",
        }
        b = MichiAIBridge(michi_ai_service=svc)
        b.sendMessage("buscar ")
        assert b.status == "FAILED"

    def test_open_route_with_no_nav_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("ir a inicio")
        assert b.status == "FAILED"

    def test_create_playlist_with_no_service_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("crear playlist")
        assert b.status == "FAILED"

    def test_diagnose_with_no_service_fails(self):
        b = MichiAIBridge(michi_ai_service=None)
        b.sendMessage("diagnosticar biblioteca")
        assert b.status == "FAILED"

    def test_all_services_none_returns_safe_defaults(self):
        b = MichiAIBridge()
        assert b._registry is not None
        assert b._nav is None
        assert b._job_svc is None
        assert b._ai_svc is None
