from __future__ import annotations
"""Test MichiAIBridge — no false success responses, all errors are typed."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


SEARCH_FAIL = {"ok": False, "error": "SEARCH_FAILED"}
SEARCH_EMPTY = {"ok": True, "results": [], "count": 0}


@pytest.fixture
def bridge():
    gs = MagicMock()
    gs.search.return_value = SEARCH_EMPTY
    tas = MagicMock()
    tas.play_track = MagicMock(return_value={"ok": False, "error": "TRACK_NOT_FOUND"})
    tas.play_album = MagicMock(return_value={"ok": False, "error": "ALBUM_NOT_FOUND"})
    tas.enqueue_track = MagicMock(return_value={"ok": False, "error": "TRACK_NOT_FOUND"})
    return MichiAIBridge(
        track_action_service=tas,
        global_search_service=gs,
        settings_service=MagicMock(),
    )


class TestNoFalseSuccess:
    def test_play_track_no_search_service(self, bridge):
        bridge._global_search = None
        bridge._tas = None
        bridge.sendMessage("reproduce Bohemian Rhapsody")
        assert bridge.status == "failed"

    def test_play_track_search_fails(self, bridge):
        bridge._global_search.search.return_value = {"ok": False, "error": "SEARCH_FAILED"}
        bridge.sendMessage("reproduce Nothing Else Matters")
        assert bridge.status == "failed"

    def test_play_track_not_found(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce canción XYZNotFound")
        assert bridge.status == "failed"

    def test_play_album_not_found(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce el álbum NoExiste")
        assert bridge.status == "failed"

    def test_enqueue_requires_track(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("encolar")
        assert bridge.status == "failed"

    def test_enqueue_no_track_name(self, bridge):
        bridge.sendMessage("encolar")
        assert bridge.status == "failed"

    def test_enqueue_not_found(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("encolar canción Inexistente")
        assert bridge.status == "failed"

    def test_search_no_query(self, bridge):
        bridge.sendMessage("buscar ")
        assert bridge.status == "failed"

    def test_open_settings_no_nav(self, bridge):
        bridge._nav = None
        bridge.sendMessage("abrir ajustes")
        assert bridge.status == "failed"

    def test_open_route_no_nav(self, bridge):
        bridge._nav = None
        bridge.sendMessage("ir a biblioteca")
        assert bridge.status == "failed"

    def test_create_playlist_no_service(self, bridge):
        bridge._playlist_svc = None
        bridge._tas = None
        bridge.sendMessage("crear playlist")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status == "failed"

    def test_show_unheard_no_mix_query(self, bridge):
        bridge.sendMessage("mostrar no escuchadas")
        assert bridge.status in ("failed", "completed")

    def test_diagnose_no_diagnostics(self, bridge):
        bridge._diagnostics = None
        bridge.sendMessage("diagnosticar biblioteca")
        assert bridge.status == "failed"

    def test_change_setting_no_settings(self, bridge):
        bridge._settings = None
        bridge.sendMessage("cambiar ajuste volumen a 50")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status == "failed"

    def test_action_unknown(self, bridge):
        result = bridge._dispatch_action("nonexistent", {"_original": ""})
        assert result.get("ok") is False

    def test_no_fake_encolado_simulado(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("encolar canción Unknown")
        assert bridge.status == "failed"
        chat = bridge.getChatHistory()
        assert "simulado" not in chat.lower()

    def test_no_fake_ok_true_from_play(self, bridge):
        bridge._tas = None
        bridge._global_search = None
        bridge.sendMessage("reproduce canción")
        assert bridge.status == "failed"

    def test_no_fake_ok_true_from_play_album(self, bridge):
        bridge._tas = None
        bridge.sendMessage("reproduce el álbum Test")
        assert bridge.status == "failed"
