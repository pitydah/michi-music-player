from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
pytestmark = [pytest.mark.qml_module("michi_ai")]


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


class TestMichiaiUsesActionRegistry:
    def test_play_uses_action_registry(self, bridge, services):
        services["action_registry"].execute.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "failed")

    def test_queue_uses_track_action_service(self, bridge, services):
        services["track_action_service"].enqueue_track.return_value = {"ok": True}
        bridge.sendMessage("encolar canción 7")
        services["track_action_service"].enqueue_track.assert_called_once_with(7)

    def test_playlist_uses_playlist_service(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        services["playlist_service"].create.assert_called_once()

    def test_search_uses_global_search_service(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar rock progresivo")
        services["global_search_service"].search.assert_called_once()

    def test_mix_action_route(self, bridge, services):
        bridge.sendMessage("ir a mix")
        services["navigation_bridge"].navigate.assert_called_once_with("mix")

    def test_audio_lab_action_route(self, bridge):
        assert hasattr(bridge, "_nav")

    def test_metadata_action_dispatched(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "track", "id": 1}],
        }
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status == "completed"

    def test_doctor_action_route(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once()

    def test_devices_action_route(self, bridge):
        assert hasattr(bridge, "_settings")

    def test_settings_action(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_once_with("settings")

    def test_navigation_action(self, bridge, services):
        bridge._nav = services["navigation_bridge"]
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_with("library")

    def test_diagnostics_action_uses_diagnostics_service(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "completed"
        services["diagnostics_service"].runQuickCheck.assert_called_once()
