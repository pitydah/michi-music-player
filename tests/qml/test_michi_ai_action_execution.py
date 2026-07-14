"""Test MichiAIBridge — states, real action execution, destructive confirmation, cancel."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


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


class TestStates:
    def test_initial_state(self, bridge):
        assert bridge.status == "idle"

    def test_valid_states(self, bridge):
        for s in ("idle", "understanding", "planning", "awaiting_confirmation",
                  "executing", "completed", "cancelled", "failed"):
            bridge._set_status(s)
            assert bridge.status == s

    def test_invalid_state_ignored(self, bridge):
        bridge._set_status("bogus")
        assert bridge.status == "idle"


class TestActionExecution:
    def test_reproducir_cancion(self, bridge, services):
        bridge.sendMessage("reproduce 42")
        services["track_action_service"].play_track.assert_called_once_with(42)

    def test_reproducir_album(self, bridge, services):
        bridge._tas.search_and_play = MagicMock()
        bridge.sendMessage("reproduce el álbum Abbey Road")
        assert bridge.status == "completed"

    def test_encolar(self, bridge, services):
        bridge.sendMessage("encolar canción 7")
        services["track_action_service"].enqueue_track.assert_called_once_with(7)

    def test_buscar(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar rock progresivo")
        services["global_search_service"].search.assert_called_once()

    def test_abrir_ruta(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once_with("library")

    def test_abrir_ajustes(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_once_with("settings")

    def test_crear_playlist_requires_confirmation(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist")
        assert bridge.status == "awaiting_confirmation"

    def test_confirm_creates_playlist(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status == "completed"
        services["playlist_service"].create.assert_called_once()

    def test_cancel_aborts_action(self, bridge):
        bridge.sendMessage("crear playlist")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("no")
        assert bridge.status == "cancelled"

    def test_diagnosticar(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "completed"
        services["diagnostics_service"].runQuickCheck.assert_called_once()

    def test_cambiar_ajuste_seguro_requires_confirmation(self, bridge, services):
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "awaiting_confirmation"

    def test_cambiar_ajuste_confirmado(self, bridge, services):
        services["settings_service"].set_.return_value = {"ok": True}
        bridge.sendMessage("cambiar ajuste volumen a 80")
        bridge.sendMessage("sí")
        assert bridge.status == "completed"
        services["settings_service"].set_.assert_called_once()

    def test_unknown_action_returns_fallback(self, bridge):
        bridge.sendMessage("qué hora es")
        assert bridge.status == "idle"
        assert len(bridge._chat_history) == 2

    def test_mostrar_no_escuchadas(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 5,
        }
        bridge.sendMessage("mostrar no escuchadas")
        assert bridge.status == "completed"
        services["global_search_service"].search.assert_called_once()


class TestCancel:
    def test_cancel_cancels_worker_task(self, bridge, services):
        bridge._current_task_id = "task_123"
        bridge.cancel()
        services["worker_manager"].cancel_task.assert_called_once_with("task_123")
        assert bridge.status == "cancelled"

    def test_cancel_during_confirmation(self, bridge):
        bridge.sendMessage("crear playlist")
        assert bridge.status == "awaiting_confirmation"
        bridge.cancel()
        assert bridge.status == "cancelled"
        assert bridge._pending_action is None

    def test_cancel_idempotent(self, bridge):
        bridge.cancel()
        assert bridge.status == "cancelled"
        bridge.cancel()
        assert bridge.status == "cancelled"


class TestScore:
    def test_score_includes_all_services(self, bridge, services):
        score = bridge.aiScore()
        assert score["score"] > 0
        assert score["has_tas"] is True
        assert score["has_search"] is True
        assert score["has_playlist"] is True
        assert score["has_settings"] is True
        assert score["has_diagnostics"] is True
        assert score["has_worker_manager"] is True

    def test_score_no_services(self):
        minimal = MichiAIBridge()
        score = minimal.aiScore()
        assert score["score"] >= 5
        assert score["has_tas"] is False
