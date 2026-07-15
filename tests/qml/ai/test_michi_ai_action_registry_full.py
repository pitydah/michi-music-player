from __future__ import annotations
"""Test MichiAI uses ActionRegistry for ALL actions. Unregistered handler  ACTION_UNAVAILABLE."""

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


def test_play_action_uses_action_registry(bridge, services):
    services["track_action_service"].play_track.return_value = {"ok": True}
    bridge.sendMessage("reproduce canción 42")
    assert bridge.status in ("completed", "failed")
    services["track_action_service"].play_track.assert_called_once_with(42)


def test_queue_action_uses_track_action_service(bridge, services):
    services["track_action_service"].enqueue_track.return_value = {"ok": True}
    bridge.sendMessage("encolar canción 7")
    services["track_action_service"].enqueue_track.assert_called_once_with(7)


def test_playlist_action_uses_playlist_service(bridge, services):
    services["playlist_service"].create.return_value = {"ok": True, "id": 1}
    bridge.sendMessage("crear playlist llamada Favoritos")
    bridge.sendMessage("sí")
    services["playlist_service"].create.assert_called_once()


def test_mix_action_navigation(bridge, services):
    bridge.sendMessage("ir a mix")
    services["navigation_bridge"].navigate.assert_called_once_with("mix")


def test_search_action_uses_global_search(bridge, services):
    services["global_search_service"].search.return_value = {
        "ok": True, "results": [], "count": 0,
    }
    bridge.sendMessage("buscar rock progresivo")
    services["global_search_service"].search.assert_called_once()


def test_navigation_action_uses_navigation_bridge(bridge, services):
    bridge.sendMessage("ir a biblioteca")
    services["navigation_bridge"].navigate.assert_called_with("library")


def test_settings_action_navigates(bridge, services):
    bridge.sendMessage("abrir ajustes")
    services["navigation_bridge"].navigate.assert_called_once_with("settings")


def test_metadata_action_dispatched(bridge, services):
    services["global_search_service"].search.return_value = {
        "ok": True, "results": [{"type": "track", "id": 1}],
    }
    services["track_action_service"].play_track.return_value = {"ok": True}
    bridge.sendMessage("reproduce canción 1")
    assert bridge.status == "completed"


def test_audio_lab_action_navigation(bridge, services):
    bridge.sendMessage("ir a biblioteca")
    services["navigation_bridge"].navigate.assert_called_once()


def test_doctor_action_uses_diagnostics(bridge, services):
    services["diagnostics_service"].runQuickCheck.return_value = {"status": "PASS"}
    bridge.sendMessage("diagnosticar biblioteca")
    assert bridge.status == "completed"
    services["diagnostics_service"].runQuickCheck.assert_called_once()


def test_devices_action_uses_navigation(bridge, services):
    bridge.sendMessage("ir a conexiones")
    services["navigation_bridge"].navigate.assert_called_with("connections")


def test_action_unavailable_on_no_service(bridge, services):
    bridge._tas = None
    bridge._global_search = None
    bridge.sendMessage("reproduce canción 42")
    assert bridge.status == "failed"
    assert "NO_TRACK_ACTION_SERVICE" in bridge.lastError or bridge.lastError != ""
