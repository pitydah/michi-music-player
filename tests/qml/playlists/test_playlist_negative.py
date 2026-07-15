"""Negative tests for Playlists: null bridge, invalid inputs, edge cases, error states."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestPlaylistNegative:

    def test_null_bridge_safe(self):
        bridge = PlaylistsBridge()
        assert bridge.playlists is not None
        assert bridge.playlists == []

    def test_create_empty_name(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.createPlaylist("")
        assert result["ok"] is True

    def test_delete_nonexistent(self):
        db = MagicMock()
        db.delete_playlist.side_effect = Exception("NOT_FOUND")
        bridge = PlaylistsBridge(db=db)
        result = bridge.deletePlaylist(999)
        assert result["ok"] is False

    def test_rename_empty_name(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.renamePlaylist(1, "")
        assert result["ok"] is True

    def test_get_detail_db_exception(self):
        db = MagicMock()
        db.get_playlist_items.side_effect = Exception("DB error")
        bridge = PlaylistsBridge(db=db)
        result = bridge.getPlaylistDetail(1)
        assert result["ok"] is False
        assert "error" in result

    def test_remove_track_db_exception(self):
        db = MagicMock()
        db.remove_track_from_playlist.side_effect = Exception("DB error")
        bridge = PlaylistsBridge(db=db)
        result = bridge.removeTrackFromPlaylist(1, 42)
        assert result["ok"] is False

    def test_add_track_invalid_path(self):
        db = MagicMock()
        db.add_track_to_playlist.return_value = True
        bridge = PlaylistsBridge(db=db)
        result = bridge.addTrackToPlaylist(1, filepath="/nonexistent/file.mp3")
        assert result["ok"] is False
        assert result["error"] == "NO_VALID_TRACK"

    def test_add_track_db_exception(self):
        db = MagicMock()
        db.add_track_to_playlist.side_effect = Exception("DB error")
        bridge = PlaylistsBridge(db=db)
        result = bridge.addTrackToPlaylist(1, track_id="42")
        assert result["ok"] is False

    def test_play_playlist_no_player(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                      title="S1", artist="A", album="Al", duration=200),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db)
        result = bridge.playPlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_play_from_index_no_player(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                      title="S1", artist="A", album="Al", duration=200),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db)
        result = bridge.playPlaylistFromIndex(1, 0)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"

    def test_playlist_score_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.playlistScore()
        assert result["has_db"] is False
        assert result["playlist_count"] == 0

    def test_batch_add_invalid_ids(self):
        db = MagicMock()
        db.add_track_to_playlist.side_effect = ValueError("invalid")
        bridge = PlaylistsBridge(db=db)
        result = bridge.batchAddTrackIds(1, ["abc", "def"])
        assert result["ok"] is True
        assert result["count"] == 0

    def test_duplicate_no_tracks_internal(self):
        db = MagicMock()
        db.get_playlist_items.side_effect = Exception("Failure")
        bridge = PlaylistsBridge(db=db)
        result = bridge.duplicatePlaylist(1)
        assert result["ok"] is False

    def test_clear_playlist_no_db_fallback(self):
        db = MagicMock()
        db.get_playlist_items.return_value = []
        bridge = PlaylistsBridge(db=db)
        result = bridge.clearPlaylist(1)
        assert result["ok"] is False

    def test_add_track_using_selection_context(self):
        sel_ctx = MagicMock()
        sel_ctx.hasSelection = True
        sel_ctx.selectedFilepath = ""
        sel_ctx.selectedTrackId = ""
        db = MagicMock()
        bridge = PlaylistsBridge(db=db, selection_context=sel_ctx)
        result = bridge.addTrackToPlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_SELECTION"
