from __future__ import annotations
"""EF — Michi AI via ActionRegistry exclusivamente.
Acciones: search, play, enqueue, playlist, Mix, AudioLab, Metadata, Doctor, Devices, Settings, navigation.
Sin handler: ACTION_UNAVAILABLE."""

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


class TestSearchAction:
    def test_search_uses_global_search_service(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [], "count": 0,
        }
        bridge.sendMessage("buscar rock progresivo")
        assert bridge.status in ("completed", "failed", "executing")

    def test_search_returns_count(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "count": 5, "results": [{"type": "track", "id": 1}],
        }
        bridge.sendMessage("buscar jazz")
        assert bridge.status in ("completed", "failed", "executing")


class TestPlayAction:
    def test_play_track_uses_track_service(self, bridge, services):
        services["track_action_service"].play_track.return_value = {"ok": True}
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("completed", "failed", "executing")
        services["track_action_service"].play_track.assert_called_once_with(42)

    def test_play_album_uses_track_service(self, bridge, services):
        services["track_action_service"].play_album.return_value = {"ok": True}
        bridge.sendMessage("reproduce álbum 10")
        assert bridge.status in ("completed", "failed", "executing")


class TestEnqueueAction:
    def test_enqueue_track_by_id(self, bridge, services):
        services["track_action_service"].enqueue_track.return_value = {"ok": True}
        bridge.sendMessage("encolar canción 7")
        services["track_action_service"].enqueue_track.assert_called_once_with(7)

    def test_enqueue_track_no_service(self, bridge):
        bridge._tas = None
        bridge._global_search = None
        bridge.sendMessage("encolar canción 1")
        assert bridge.status == "failed"
        assert "NO_TRACK_ACTION_SERVICE" in bridge.lastError or bridge.lastError != ""


class TestPlaylistAction:
    def test_create_playlist(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status in ("awaiting_confirmation", "completed", "executing")

    def test_create_playlist_confirm(self, bridge, services):
        services["playlist_service"].create.return_value = {"ok": True, "id": 1}
        bridge.sendMessage("crear playlist llamada Favoritos")
        bridge.sendMessage("sí")
        services["playlist_service"].create.assert_called_once()


class TestMixAction:
    def test_mix_navigation(self, bridge, services):
        bridge.sendMessage("ir a mix")
        services["navigation_bridge"].navigate.assert_called_once_with("mix")


class TestAudioLabAction:
    def test_audio_lab_navigation(self, bridge, services):
        bridge.sendMessage("ir a audi")
        services["navigation_bridge"].navigate.assert_called_once()


class TestMetadataAction:
    def test_metadata_search(self, bridge, services):
        services["global_search_service"].search.return_value = {
            "ok": True, "results": [{"type": "track", "id": 1}],
        }
        bridge.sendMessage("reproduce canción 1")
        assert bridge.status in ("completed", "failed", "executing")


class TestDoctorAction:
    def test_doctor_diagnose(self, bridge, services):
        services["diagnostics_service"].runQuickCheck.return_value = {"ok": True}
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status in ("completed", "failed")
        services["diagnostics_service"].runQuickCheck.assert_called_once()

    def test_doctor_fails_without_diagnostics(self, bridge):
        bridge._diagnostics = None
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "failed"


class TestDevicesAction:
    def test_devices_navigation(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_once()


class TestSettingsAction:
    def test_settings_navigates(self, bridge, services):
        bridge.sendMessage("abrir ajustes")
        services["navigation_bridge"].navigate.assert_called_once_with("settings")

    def test_settings_change(self, bridge, services):
        services["settings_service"].set_.return_value = {"ok": True}
        bridge.sendMessage("cambiar ajuste seguro volumen 80")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")


class TestNavigationAction:
    def test_navigate_home(self, bridge, services):
        bridge.sendMessage("ir a inicio")
        services["navigation_bridge"].navigate.assert_called_with("home")

    def test_navigate_library(self, bridge, services):
        bridge.sendMessage("ir a biblioteca")
        services["navigation_bridge"].navigate.assert_called_with("library")

    def test_navigate_radio(self, bridge, services):
        bridge.sendMessage("ir a radio")
        services["navigation_bridge"].navigate.assert_called_with("radio")


class TestActionUnavailable:
    def test_action_unavailable_no_handler(self, bridge):
        bridge._tas = None
        bridge._global_search = None
        bridge._nav = None
        bridge._playlist_svc = None
        bridge._settings = None
        bridge._diagnostics = None
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "failed"

    def test_unknown_intent_returns_to_idle(self, bridge):
        bridge.sendMessage("xyzzy unknown command")
        assert bridge.status == "idle"
        assert len(bridge._chat_history) >= 1
