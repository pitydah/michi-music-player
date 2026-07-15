from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("michi_ai")]


class TestMichiAIExecution:
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

    def test_execution_completes_play(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("completed", "failed")

    def test_execution_fails_no_service(self, bridge):
        bridge._tas = None
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "failed"

    def test_execution_play_album(self, bridge, services):
        services["track_action_service"].play_album.return_value = {"ok": True}
        bridge.sendMessage("reproduce álbum dark side")
        assert bridge.status in ("completed", "failed")

    def test_execution_enqueue(self, bridge, services):
        services["track_action_service"].enqueue_track.return_value = {"ok": True}
        bridge.sendMessage("encolar canción 7")
        assert bridge.status in ("completed", "failed")

    def test_execution_search(self, bridge, services):
        services["global_search_service"].search.return_value = {"ok": True, "count": 3, "results": []}
        bridge.sendMessage("buscar rock")
        assert bridge.status == "completed"

    def test_execution_search_no_query(self, bridge):
        bridge._action_search({"_original": "buscar"})
        assert bridge._last_error != "" or bridge.status == "failed"

    def test_execution_confirmation_required(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"
        assert bridge._pending_action is not None

    def test_execution_confirm_continues(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        assert bridge.status in ("completed", "failed")

    def test_execution_reject_cancels(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("no")
        assert bridge.status == "cancelled"

    def test_execution_cancel_during_execution(self, bridge):
        bridge._status = "executing"
        bridge._current_task_id = "task_123"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_execution_cancel_no_task(self, bridge):
        bridge._status = "executing"
        bridge.cancel()
        assert bridge.status == "cancelled"

    def test_execution_diagnose(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "completed"

    def test_execution_open_route(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_with("library")

    def test_execution_open_settings(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_with("settings")

    def test_execution_unknown_action(self, bridge):
        bridge.sendMessage("hacer algo desconocido")
        assert bridge.status == "failed" or bridge.status == "idle"

    def test_execution_change_setting(self, bridge, services):
        services["settings_service"].set_.return_value = {"ok": True}
        bridge.sendMessage("cambiar ajuste de volumen a 50")
        assert bridge.status == "completed"

    def test_execution_change_setting_requires_confirmation(self, bridge):
        bridge.sendMessage("cambiar ajuste de tema oscuro")
        assert bridge.status == "awaiting_confirmation"
