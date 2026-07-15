<<<<<<< Updated upstream
"""Test Michi AI action execution flow with confirmation."""

=======
<<<<<<< HEAD
=======
"""Test Michi AI action execution flow with confirmation."""

>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
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
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("michi_ai")]
>>>>>>> Stashed changes


class TestMichiAIExecution:
    def test_play_track_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        services["track_action_service"].play_track.assert_called_once_with(42)
        assert bridge.status in ("completed", "executing")

    def test_play_album_execution(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "album", "title": "Dark Side"}],
        }
        bridge.sendMessage("reproduce álbum Dark Side")
        assert bridge.status in ("completed", "executing", "failed")

    def test_enqueue_execution(self, bridge, services):
        services["track_action_service"].enqueue_track.return_value = {"ok": True}
        bridge.sendMessage("encolar canción 7")
        services["track_action_service"].enqueue_track.assert_called_once_with(7)
        assert bridge.status in ("completed", "executing")

    def test_search_execution(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar rock progresivo")
        services["global_search_service"].search.assert_called_once()

    def test_navigate_execution(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once_with("library")

    def test_create_playlist_needs_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"

    def test_confirm_playlist_creation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        services["playlist_service"].create.assert_called_once()

    def test_reject_playlist_creation(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None
        assert bridge.status == "cancelled"

    def test_diagnostics_execution(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"status": "PASS"}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status in ("completed", "executing")
        services["diagnostics_service"].runQuickCheck.assert_called_once()

    def test_settings_navigation_execution(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_once_with("settings")

    def test_add_songs_to_playlist_needs_confirmation(self, bridge, services):
        services["playlist_service"].batch_add.return_value = {"ok": True}
        bridge.sendMessage("agregar canciones a playlist 5")
        assert bridge.status == "awaiting_confirmation"
<<<<<<< Updated upstream
=======
=======
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


class TestMichiAIExecution:
    def test_play_track_execution(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        services["track_action_service"].play_track.assert_called_once_with(42)
        assert bridge.status in ("completed", "executing")

    def test_play_album_execution(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "album", "title": "Dark Side"}],
        }
        bridge.sendMessage("reproduce álbum Dark Side")
        assert bridge.status in ("completed", "executing", "failed")

    def test_enqueue_execution(self, bridge, services):
        services["track_action_service"].enqueue_track.return_value = {"ok": True}
        bridge.sendMessage("encolar canción 7")
        services["track_action_service"].enqueue_track.assert_called_once_with(7)
        assert bridge.status in ("completed", "executing")

    def test_search_execution(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar rock progresivo")
        services["global_search_service"].search.assert_called_once()

    def test_navigate_execution(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once_with("library")

    def test_create_playlist_needs_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "awaiting_confirmation"

    def test_confirm_playlist_creation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        services["playlist_service"].create.assert_called_once()

    def test_reject_playlist_creation(self, bridge):
        bridge._pending_action = {"name": "crear playlist", "description": "crear playlist"}
        bridge.sendMessage("no")
        assert bridge._pending_action is None
        assert bridge.status == "cancelled"

    def test_diagnostics_execution(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"status": "PASS"}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status in ("completed", "executing")
        services["diagnostics_service"].runQuickCheck.assert_called_once()

    def test_settings_navigation_execution(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_once_with("settings")

    def test_add_songs_to_playlist_needs_confirmation(self, bridge, services):
        services["playlist_service"].batch_add.return_value = {"ok": True}
        bridge.sendMessage("agregar canciones a playlist 5")
        assert bridge.status == "awaiting_confirmation"
>>>>>>> Stashed changes

    def test_change_setting_needs_confirmation(self, bridge, services):
        services["settings_service"].set_.return_value = True
        bridge.sendMessage("cambiar ajuste volumen 80")
        assert bridge.status == "awaiting_confirmation"

    def test_show_unheard_execution(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "count": 15,
        }
        bridge.sendMessage("mostrar no escuchadas")
        assert bridge.status in ("completed", "executing")

    def test_create_playlist_with_destructive_flag(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Nueva")
        assert bridge.status == "awaiting_confirmation"

    def test_action_completed_result_message(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        last = bridge._chat_history[-1]
        assert "Hecho" in last["text"]

    def test_action_failed_result_message(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": False, "error": "NOT_FOUND"}
        bridge.sendMessage("reproduce canción 999")
        last = bridge._chat_history[-1]
        assert "Error" in last["text"]
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
