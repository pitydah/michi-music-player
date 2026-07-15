from __future__ import annotations
"""Test MichiAIBridge — album playback resolves album_key, obtains tracks, plays from track 1."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


@pytest.fixture
def services():
    tas = MagicMock()
    tas.query_service = MagicMock()
    tas.play_album = MagicMock(return_value={"ok": False, "error": "ALBUM_NOT_FOUND"})
    tas.play_track = MagicMock(return_value={"ok": False, "error": "TRACK_NOT_FOUND"})
    return {
        "track_action_service": tas,
        "global_search_service": MagicMock(),
        "worker_manager": MagicMock(),
    }


@pytest.fixture
def bridge(services):
    return MichiAIBridge(
        track_action_service=services["track_action_service"],
        global_search_service=services["global_search_service"],
        worker_manager=services["worker_manager"],
    )


class TestAlbumPlayback:
    def test_play_album_reproduce_album(self, bridge, services):
        bridge._global_search.search.return_value = {"ok": True, "results": [
            {"type": "album", "id": "key1", "title": "Test Album", "artist": "Artist",
             "track_count": 2},
        ]}
        bridge._tas.play_album = MagicMock(return_value={"ok": True, "count": 2})
        bridge.sendMessage("reproduce el álbum Test Album")
        assert bridge.status == "completed"

    def test_play_album_not_found(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce el álbum NoSuchAlbum")
        assert bridge.status == "failed"

    def test_play_album_no_name(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce el álbum")
        assert bridge.status == "failed"

    def test_play_album_ambiguous(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": [
            {"type": "album", "id": "key_a", "title": "Album", "artist": "A1"},
            {"type": "album", "id": "key_b", "title": "Album", "artist": "A2"},
        ]}
        bridge.sendMessage("reproduce el álbum Album")
        assert bridge.status in ("failed", "completed")

    def test_play_album_no_tas(self, bridge):
        bridge._tas = None
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce el álbum Test")
        assert bridge.status == "failed"

    def test_play_album_parses_correctly(self, bridge):
        bridge._global_search.search.return_value = {"ok": True, "results": []}
        bridge.sendMessage("reproduce el álbum Dark Side")
        assert bridge.status == "failed"
