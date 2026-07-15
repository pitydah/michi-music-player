"""Tests for SmartPlaylistEditorPage: rule management, preview, save."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestSmartPlaylist:

    def test_bridge_default_state(self):
        bridge = PlaylistsBridge()
        assert bridge.playlists == []

    def test_save_queue_as_playlist_empty_name(self):
        bridge = PlaylistsBridge()
        result = bridge.saveQueueAsPlaylist("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_NAME"

    def test_save_queue_as_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.saveQueueAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_save_queue_as_playlist_no_tracks(self):
        db = MagicMock()
        player = MagicMock()
        player.get_queue.return_value = []
        bridge = PlaylistsBridge(db=db, player_service=player)
        result = bridge.saveQueueAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error"] == "NO_TRACKS"

    def test_save_queue_as_playlist_with_tracks(self):
        db = MagicMock()
        db.create_playlist.return_value = 42
        player = MagicMock()
        from unittest.mock import MagicMock as M
        item = M()
        item.filepath = "/music/song1.mp3"
        player.get_queue.return_value = [item]
        bridge = PlaylistsBridge(db=db, player_service=player)
        result = bridge.saveQueueAsPlaylist("Queue Playlist")
        assert result["ok"] is True
        assert result["id"] == 42

    def test_save_queue_with_service(self):
        svc = MagicMock()
        svc.save_queue.return_value = {"ok": True, "id": 99}
        player = MagicMock()
        bridge = PlaylistsBridge(playlist_service=svc, player_service=player)
        result = bridge.saveQueueAsPlaylist("Service Queue")
        assert result["ok"] is True
        assert result["id"] == 99

    def test_playlist_score_empty(self):
        bridge = PlaylistsBridge()
        result = bridge.playlistScore()
        assert result["score"] >= 0
        assert result["has_db"] is False

    def test_playlist_score_with_db(self):
        db = MagicMock()
        db.get_playlists.return_value = [{"id": 1, "name": "Test", "track_count": 5}]
        db.get_playlist_items.return_value = []
        db.update_playlist.return_value = True
        db.delete_playlist.return_value = True
        bridge = PlaylistsBridge(db=db)
        bridge.refresh()
        result = bridge.playlistScore()
        assert result["score"] > 0
        assert result["has_db"] is True
        assert result["can_create"] is True
        assert result["can_delete"] is True

    def test_selection_context_contract(self):
        sel_ctx = MagicMock()
        sel_ctx.hasSelection = True
        sel_ctx.selectedFilepath = "/music/selected.mp3"
        bridge = PlaylistsBridge(selection_context=sel_ctx)
        assert bridge._sel_ctx is sel_ctx

    def test_selection_context_integration(self):
        sel_ctx = MagicMock()
        sel_ctx.hasSelection = True
        sel_ctx.selectedFilepath = "/music/selected.mp3"
        db = MagicMock()
        db.add_track_to_playlist.return_value = True
        bridge = PlaylistsBridge(db=db, selection_context=sel_ctx)
        result = bridge.addTrackToPlaylist(1)
        assert result["ok"] is True

    def test_bridge_add_selected_track(self):
        db = MagicMock()
        sel_ctx = MagicMock()
        sel_ctx.hasSelection = True
        sel_ctx.selectedFilepath = "/music/t.mp3"
        bridge = PlaylistsBridge(db=db, selection_context=sel_ctx)
        result = bridge.addSelectedTrackToPlaylist(1)
        assert result["ok"] is True

    def test_playlist_created_refresh(self):
        db = MagicMock()
        db.create_playlist.return_value = 1
        db.get_playlists.return_value = [{"id": 1, "name": "New", "track_count": 0}]
        bridge = PlaylistsBridge(db=db)
        bridge.createPlaylist("New")
        assert len(bridge.playlists) == 1

    def test_playlist_deleted_refresh(self):
        db = MagicMock()
        db.delete_playlist.return_value = True
        db.get_playlists.return_value = []
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Old"}]
        bridge.deletePlaylist(1)
        assert len(bridge.playlists) == 0
