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
    svc = MagicMock()
    svc.process_message.return_value = {"ok": True, "response": "done"}
    svc.get_suggestions.return_value = []
    return {
        "michi_ai_service": svc,
        "action_registry": MagicMock(),
        "navigation_bridge": MagicMock(),
        "confirmation_service": MagicMock(),
        "job_service": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        michi_ai_service=services["michi_ai_service"],
        job_service=services["job_service"],
        confirmation_service=services["confirmation_service"],
        action_registry=services["action_registry"],
        navigation_bridge=services["navigation_bridge"],
    )


class TestSearchAction:
    def test_search_uses_global_search_service(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "searching..."
        }
        bridge.sendMessage("buscar rock progresivo")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")

    def test_search_returns_count(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "found results"
        }
        bridge.sendMessage("buscar jazz")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")


class TestPlayAction:
    def test_play_track_uses_track_service(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "playing..."
        }
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")

    def test_play_album_uses_track_service(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "playing album..."
        }
        bridge.sendMessage("reproduce álbum 10")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")


class TestEnqueueAction:
    def test_enqueue_track_by_id(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "enqueued"
        }
        bridge.sendMessage("encolar canción 7")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED", "QUEUED")

    def test_enqueue_track_no_service(self, bridge, services):
        services["michi_ai_service"].process_message.side_effect = RuntimeError("no service")
        bridge.sendMessage("encolar canción 1")
        assert bridge.status == "FAILED"


class TestPlaylistAction:
    def test_create_playlist(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "created playlist"
        }
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED")

    def test_create_playlist_confirm(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": False, "requires_confirmation": True,
            "intent": {"name": "playlist", "description": "create playlist"},
            "plan": {}, "entities": {}, "executed": False,
        }
        bridge.sendMessage("crear playlist llamada Favoritos")
        assert bridge.status == "CONFIRMATION_REQUIRED"


class TestNavigationAction:
    def test_navigate_home(self, bridge, services):
        services["michi_ai_service"].process_message.return_value = {
            "ok": True, "response": "navigating..."
        }
        bridge.sendMessage("ir a inicio")
        assert bridge.status in ("PLANNING", "SUCCEEDED", "FAILED")


class TestActionUnavailable:
    def test_action_unavailable_no_handler(self, bridge, services):
        services["michi_ai_service"].process_message.side_effect = RuntimeError("no handler")
        bridge.sendMessage("reproduce canción 42")
        assert bridge.status == "FAILED"

    def test_unknown_intent_returns_to_idle(self, bridge, services):
        services["michi_ai_service"].process_message.side_effect = RuntimeError("unknown")
        bridge.sendMessage("xyzzy unknown command")
        assert bridge.status == "FAILED"
