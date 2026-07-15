from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIWorkflow:
    """End-to-end workflow tests for Michi AI."""

    @pytest.fixture
    def services(self):
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
    def bridge(self, services):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        return MichiAIBridge(**services)

    def test_workflow_play_track_ok(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "completed"

    def test_workflow_play_track_no_id_fallback(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "track", "id": 1}],
        }
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción bohemian rhapsody")
        assert bridge.status in ("completed", "failed")

    def test_workflow_search_and_play(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "track", "id": 5}], "count": 1,
        }
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("buscar yesterday")
        services["global_search_service"].search.assert_called()
        assert bridge.status == "completed"

    def test_workflow_create_playlist_confirm(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 10}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        assert bridge._pending_action is not None

    def test_workflow_create_playlist_confirm_yes(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 10}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        services["playlist_service"].create.assert_called_once()
        assert bridge.status == "completed"

    def test_workflow_create_playlist_confirm_no(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 10}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("no")
        assert bridge.status == "cancelled"

    def test_workflow_navigate_library(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_with("library")

    def test_workflow_navigate_home(self, bridge, services):
        bridge.sendMessage("ir a inicio")
        services["navigation_bridge"].navigate.assert_called_with("home")

    def test_workflow_navigate_settings(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_with("settings")

    def test_workflow_diagnose_library(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        services["diagnostics_service"].runQuickCheck.assert_called_once()
        assert bridge.status == "completed"

    def test_workflow_multiple_sequential_actions(self, bridge, services):
        services["navigation_bridge"].navigate.return_value = None
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "track", "id": 1}], "count": 1,
        }
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("ir a biblioteca")
        bridge.sendMessage("buscar progressive rock")
        assert bridge.status == "completed"

    def test_workflow_undo_last_action(self, bridge, services):
        bridge.sendMessage("reproduce canción 1")
        history_len = len(bridge._chat_history)
        assert history_len > 0

    def test_workflow_cancel_during_execution(self, bridge, services):
        bridge._status = "executing"
        bridge._current_task_id = "task_42"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_workflow_change_setting_then_revert(self, bridge, services):
        services["settings_service"].set_.return_value = {"ok": True}
        bridge.sendMessage("cambiar ajuste de volumen a 50")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "failed")

    def test_workflow_error_recovery(self, bridge, services):
        services["track_action_service"].play_track.side_effect = Exception("Connection error")
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "failed"

    def test_workflow_refreshes_suggestions(self, bridge, services):
        services["context_service"].get_suggestions.return_value = [
            {"title": "Test", "description": "Desc", "action": "navigate", "route": "library"},
        ]
        bridge.refresh()
        assert len(bridge.suggestions) == 1
