"""Tests for playlist actions: create, rename, duplicate, delete, reorder, add/remove tracks."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestPlaylistActions:

    def test_create_playlist(self):
        db = MagicMock()
        db.create_playlist.return_value = 42
        bridge = PlaylistsBridge(db=db)
        result = bridge.createPlaylist("New Playlist")
        assert result["ok"] is True
        assert result["id"] == 42
        db.create_playlist.assert_called_once_with("New Playlist")

    def test_create_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.createPlaylist("Test")
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_delete_playlist(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Test"}]
        result = bridge.deletePlaylist(1)
        assert result["ok"] is True
        db.delete_playlist.assert_called_once_with(1)

    def test_delete_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.deletePlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_rename_playlist(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Old"}]
        result = bridge.renamePlaylist(1, "New Name")
        assert result["ok"] is True
        db.update_playlist.assert_called_once_with(1, name="New Name")

    def test_rename_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.renamePlaylist(1, "New")
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_duplicate_playlist(self):
        db = MagicMock()
        db.create_playlist.return_value = 99
        items = [
            MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                      title="S1", artist="A", album="Al", duration=100),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Original"}]
        result = bridge.duplicatePlaylist(1)
        assert result["ok"] is True
        assert result["id"] == 99
        assert "copia" in result["name"]

    def test_duplicate_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.duplicatePlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_duplicate_empty_playlist(self):
        db = MagicMock()
        db.get_playlist_items.return_value = []
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Empty"}]
        result = bridge.duplicatePlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_TRACKS"

    def test_add_track_by_path(self):
        db = MagicMock()
        db.add_track_to_playlist.return_value = True
        bridge = PlaylistsBridge(db=db)
        result = bridge.addTrackToPlaylist(1, filepath="/music/song.mp3")
        assert result["ok"] is True

    def test_add_track_by_id(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.addTrackToPlaylist(1, track_id="42")
        assert result["ok"] is True

    def test_add_track_no_selection(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.addTrackToPlaylist(1, filepath="", track_id="")
        assert result["ok"] is False
        assert result["error"] == "NO_SELECTION"

    def test_add_track_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.addTrackToPlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_batch_add_tracks(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        tracks = [
            {"track_id": 1, "filepath": "/m/s1.mp3"},
            {"track_id": 2, "filepath": "/m/s2.mp3"},
        ]
        result = bridge.batchAddTracks(1, tracks)
        assert result["ok"] is True
        assert result["count"] == 2

    def test_batch_add_track_ids(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.batchAddTrackIds(1, [10, 20, 30])
        assert result["ok"] is True
        assert result["count"] == 3

    def test_reorder_track(self):
        db = MagicMock()
        db.reorder_playlist_track.return_value = True
        bridge = PlaylistsBridge(db=db)
        result = bridge.reorderTrack(1, 0, 2)
        assert result["ok"] is True
        db.reorder_playlist_track.assert_called_once_with(1, 0, 2)

    def test_reorder_track_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.reorderTrack(1, 0, 2)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_reorder_unsupported(self):
        db = MagicMock()
        del db.reorder_playlist_track
        bridge = PlaylistsBridge(db=db)
        result = bridge.reorderTrack(1, 0, 2)
        assert result["ok"] is False
        assert result["error"] == "UNSUPPORTED"
