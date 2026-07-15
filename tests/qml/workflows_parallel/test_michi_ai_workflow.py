"""Workflow test: Prompt → preview → confirm → execute → show result."""

"""Workflow test: Prompt → preview → confirm → execute → show result."""

from __future__ import annotations

from unittest.mock import MagicMock

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
pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIWorkflow:
    def test_workflow_prompt_preview_confirm_execute(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "executing")
        assert services["playlist_service"].create.called

    def test_workflow_prompt_reject_cancels(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None
        assert bridge.status == "cancelled"

    def test_workflow_prompt_execute_show_result(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "executing")
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"]

    def test_workflow_prompt_fails_shows_error(self, bridge, services):
        services["track_action_service"].play_track.return_value = {
            "ok": False, "error": "NOT_FOUND",
        }
        bridge.sendMessage("reproduce canción 999")
        assert bridge.status == "failed"
        last = bridge._chat_history[-1]
        assert "Error" in last["text"]

    def test_workflow_full_cycle(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_workflow_destructive_requires_confirm(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "awaiting_confirmation"

    def test_workflow_confirm_then_execute(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "executing")

    def test_workflow_execute_without_confirm_skips(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("executing", "completed")

    def test_workflow_navigate_prompt(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once_with("library")

    def test_workflow_search_prompt(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar jazz")
        services["global_search_service"].search.assert_called_once()

    def test_workflow_unknown_prompt_fallback(self, bridge):
        bridge.sendMessage("haz algo mágico")
        last = bridge._chat_history[-1]
        assert "No entendí" in last["text"]

    def test_workflow_cancel_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_workflow_execution_progress_tracking(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 10")
        assert bridge.status in ("executing", "completed")

    def test_workflow_partial_execution_shows_result(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"] or "Error" in last["text"]
        assert bridge.status == "failed"

    def test_workflow_refreshes_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Desc", "action": "navigate", "route": "library"},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 1


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


class TestMichiAIWorkflow:
    def test_workflow_prompt_preview_confirm_execute(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "executing")
        assert services["playlist_service"].create.called

    def test_workflow_prompt_reject_cancels(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None
        assert bridge.status == "cancelled"

    def test_workflow_prompt_execute_show_result(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "executing")
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"]

    def test_workflow_prompt_fails_shows_error(self, bridge, services):
        services["track_action_service"].play_track.return_value = {
            "ok": False, "error": "NOT_FOUND",
        }
        bridge.sendMessage("reproduce canción 999")
        assert bridge.status == "failed"
        last = bridge._chat_history[-1]
        assert "Error" in last["text"]

    def test_workflow_full_cycle(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 2

    def test_workflow_destructive_requires_confirm(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "awaiting_confirmation"

    def test_workflow_confirm_then_execute(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Test")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "executing")

    def test_workflow_execute_without_confirm_skips(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("executing", "completed")

    def test_workflow_navigate_prompt(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once_with("library")

    def test_workflow_search_prompt(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar jazz")
        services["global_search_service"].search.assert_called_once()

    def test_workflow_unknown_prompt_fallback(self, bridge):
        bridge.sendMessage("haz algo mágico")
        last = bridge._chat_history[-1]
        assert "No entendí" in last["text"]

    def test_workflow_cancel_during_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_workflow_execution_progress_tracking(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 10")
        assert bridge.status in ("executing", "completed")

    def test_workflow_partial_execution_shows_result(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert len(bridge._chat_history) >= 1
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"] or "Error" in last["text"]
