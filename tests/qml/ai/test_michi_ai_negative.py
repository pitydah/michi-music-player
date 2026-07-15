"""Test Michi AI negative scenarios: missing service, execution failure, rejected action, cancellation."""

"""Test Michi AI negative scenarios: missing service, execution failure, rejected action, cancellation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


pytestmark = pytest.mark.isolation
pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAINegative:
    def test_missing_service_play_track_fails(self):
        services = {k: None for k in (
            "ai_controller", "context_service", "plan_builder", "tool_registry",
            "action_registry", "navigation_bridge", "track_action_service",
            "playlist_service", "global_search_service", "settings_service",
            "diagnostics_service", "worker_manager",
        )}
        b = MichiAIBridge(**services)
        b.sendMessage("reproduce canción 42")
        assert b.status == "failed"
        assert "NO_TRACK_ACTION_SERVICE" in b.lastError or b.lastError != ""

    def test_missing_navigation_service(self):
        b = MichiAIBridge()
        b.sendMessage("ir a biblioteca")
        assert b.status == "failed"

    def test_missing_search_service(self):
        services = {
            "track_action_service": MagicMock(),
            "global_search_service": None,
            "navigation_bridge": None,
            "playlist_service": None,
            "settings_service": None,
            "diagnostics_service": None,
            "worker_manager": None,
            "ai_controller": None,
            "context_service": None,
            "plan_builder": None,
            "tool_registry": None,
            "action_registry": None,
        }
        b = MichiAIBridge(**services)
        b.sendMessage("buscar rock")
        assert b.status == "failed"
        assert b.lastError != ""

    def test_execution_failure_propagates_error(self):
        tas = MagicMock()
        tas.play_track.return_value = {"ok": False, "error": "NO_SERVICE"}
        services = {
            "track_action_service": tas,
            "global_search_service": None,
            "navigation_bridge": None,
            "playlist_service": None,
            "settings_service": None,
            "diagnostics_service": None,
            "worker_manager": None,
            "ai_controller": None,
            "context_service": None,
            "plan_builder": None,
            "tool_registry": None,
            "action_registry": None,
        }
        b = MichiAIBridge(**services)
        b.sendMessage("reproduce canción 42")
        assert b.status == "failed"
        assert len(b._chat_history) >= 1
        assert b._chat_history[-1]["role"] == "assistant"

    def test_rejected_action_clears_pending(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.sendMessage("no")
        assert b._pending_action is None
        assert b.status == "cancelled"

    def test_cancellation_clears_pending(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.cancel()
        assert b._pending_action is None
        assert b.status == "cancelled"

    def test_cancelled_action_does_not_execute(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.cancel()
        assert b._chat_history == []

    def test_none_bridge_returns_null_safe(self):
        page = type("MockPage", (), {"ai": None})()
        assert page.ai is None

    def test_destructive_action_requires_confirmation(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test_destructive", "description": "delete files"}
        assert b._pending_action is not None
        b.sendMessage("no")
        assert b._pending_action is None

    def test_unavailable_action_returns_error(self):
        b = MichiAIBridge()
        result = b._dispatch_action("nonexistent", {"name": "nonexistent"})
        assert result["ok"] is False
        assert "Acción desconocida" in result["error"]

    def test_play_with_no_track_id_fails(self):
        b = MichiAIBridge()
        result = b._action_play({"_original": "reproduce canción sin_id"})
        assert result["ok"] is False

    def test_enqueue_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_enqueue({"_original": "encolar canción 42"})
        assert result["ok"] is False

    def test_search_with_empty_query_fails(self):
        b = MichiAIBridge()
        result = b._action_search({"_original": "buscar "})
        assert result["ok"] is False

    def test_open_route_with_no_nav_fails(self):
        b = MichiAIBridge()
        result = b._action_open_route({"_original": "ir a inicio"})
        assert result["ok"] is False

    def test_create_playlist_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_create_playlist({"_original": "crear playlist"})
        assert result["ok"] is False

    def test_bridge_unknown_intent_returns_fallback(self, bridge):
        bridge.sendMessage("zxcvbnm")
        assert any("No entendí" in m.get("text", "") for m in bridge._chat_history if m.get("role") == "assistant")


pytestmark = pytest.mark.isolation


class TestMichiAINegative:
    def test_missing_service_play_track_fails(self):
        services = {k: None for k in (
            "ai_controller", "context_service", "plan_builder", "tool_registry",
            "action_registry", "navigation_bridge", "track_action_service",
            "playlist_service", "global_search_service", "settings_service",
            "diagnostics_service", "worker_manager",
        )}
        b = MichiAIBridge(**services)
        b.sendMessage("reproduce canción 42")
        assert b.status == "failed"
        assert "NO_TRACK_ACTION_SERVICE" in b.lastError or b.lastError != ""

    def test_missing_navigation_service(self):
        b = MichiAIBridge()
        b.sendMessage("ir a biblioteca")
        assert b.status == "failed"

    def test_missing_search_service(self):
        services = {
            "track_action_service": MagicMock(),
            "global_search_service": None,
            "navigation_bridge": None,
            "playlist_service": None,
            "settings_service": None,
            "diagnostics_service": None,
            "worker_manager": None,
            "ai_controller": None,
            "context_service": None,
            "plan_builder": None,
            "tool_registry": None,
            "action_registry": None,
        }
        b = MichiAIBridge(**services)
        b.sendMessage("buscar rock")
        assert b.status == "failed"
        assert b.lastError != ""

    def test_execution_failure_propagates_error(self):
        tas = MagicMock()
        tas.play_track.return_value = {"ok": False, "error": "NO_SERVICE"}
        services = {
            "track_action_service": tas,
            "global_search_service": None,
            "navigation_bridge": None,
            "playlist_service": None,
            "settings_service": None,
            "diagnostics_service": None,
            "worker_manager": None,
            "ai_controller": None,
            "context_service": None,
            "plan_builder": None,
            "tool_registry": None,
            "action_registry": None,
        }
        b = MichiAIBridge(**services)
        b.sendMessage("reproduce canción 42")
        assert b.status == "failed"
        assert len(b._chat_history) >= 1
        assert b._chat_history[-1]["role"] == "assistant"

    def test_rejected_action_clears_pending(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.sendMessage("no")
        assert b._pending_action is None
        assert b.status == "cancelled"

    def test_cancellation_clears_pending(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.cancel()
        assert b._pending_action is None
        assert b.status == "cancelled"

    def test_cancelled_action_does_not_execute(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test", "description": "test"}
        b.cancel()
        assert b._chat_history == []

    def test_none_bridge_returns_null_safe(self):
        page = type("MockPage", (), {"ai": None})()
        assert page.ai is None

    def test_destructive_action_requires_confirmation(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test_destructive", "description": "delete files"}
        assert b._pending_action is not None
        b.sendMessage("no")
        assert b._pending_action is None

    def test_unavailable_action_returns_error(self):
        b = MichiAIBridge()
        result = b._dispatch_action("nonexistent", {"name": "nonexistent"})
        assert result["ok"] is False
        assert "Acción desconocida" in result["error"]

    def test_play_with_no_track_id_fails(self):
        b = MichiAIBridge()
        result = b._action_play({"_original": "reproduce canción sin_id"})
        assert result["ok"] is False

    def test_enqueue_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_enqueue({"_original": "encolar canción 42"})
        assert result["ok"] is False

    def test_search_with_empty_query_fails(self):
        b = MichiAIBridge()
        result = b._action_search({"_original": "buscar "})
        assert result["ok"] is False

    def test_open_route_with_no_nav_fails(self):
        b = MichiAIBridge()
        result = b._action_open_route({"_original": "ir a inicio"})
        assert result["ok"] is False

    def test_create_playlist_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_create_playlist({"_original": "crear playlist"})
        assert result["ok"] is False

    def test_add_songs_with_no_id_fails(self):
        b = MichiAIBridge()
        result = b._action_add_songs({"_original": "agregar canciones"})
        assert result["ok"] is False

    def test_change_setting_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_change_setting({"_original": "cambiar ajuste volumen 50"})
        assert result["ok"] is False

    def test_diagnose_with_no_service_fails(self):
        b = MichiAIBridge()
        result = b._action_diagnose({})
        assert result["ok"] is False

    def test_all_services_none_returns_safe_defaults(self):
        b = MichiAIBridge()
        assert b.status == "idle"
        assert b.suggestions == []
        assert b.lastError == ""
        assert b._chat_history == []

    def test_confirm_without_pending_noops(self):
        b = MichiAIBridge()
        b.sendMessage("sí")
        last = b._chat_history[-1]
        assert "no hay" in last["text"].lower()

    def test_cancel_during_understanding(self):
        b = MichiAIBridge()
        b.cancel()
        assert b.status == "cancelled"

    def test_memory_cleanup_after_cancel(self):
        b = MichiAIBridge()
        b._pending_action = {"name": "test"}
        b.cancel()
        assert b._pending_action is None
        assert b._last_error == ""
