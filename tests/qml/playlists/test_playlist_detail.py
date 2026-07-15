"""Tests for PlaylistDetailPage: bridge interactions, track loading, CRUD."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestPlaylistDetail:

    def test_get_playlist_detail_empty(self):
        db = MagicMock()
        db.get_playlist_items.return_value = []
        bridge = PlaylistsBridge(db=db)
        result = bridge.getPlaylistDetail(1)
        assert result["ok"] is True
        assert result["tracks"] == []
        assert result["count"] == 0

    def test_get_playlist_detail_with_tracks(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="uid1", filepath="/music/song1.mp3",
                      title="Song1", artist="A1", album="Al1", duration=200),
            MagicMock(id=2, track_uid="uid2", filepath="/music/song2.mp3",
                      title="Song2", artist="A2", album="Al2", duration=180),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db)
        result = bridge.getPlaylistDetail(1)
        assert result["ok"] is True
        assert result["count"] == 2
        assert result["tracks"][0]["title"] == "Song1"
        assert result["tracks"][1]["title"] == "Song2"

    def test_get_playlist_detail_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.getPlaylistDetail(1)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_get_playlist_detail_missing_track(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="uid1", filepath="",
                      title="Missing", artist="A1", album="Al1", duration=0),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db)
        result = bridge.getPlaylistDetail(1)
        assert result["ok"] is True
        assert result["tracks"][0]["missing"] is True

    def test_remove_track_from_playlist(self):
        db = MagicMock()
        bridge = PlaylistsBridge(db=db)
        result = bridge.removeTrackFromPlaylist(1, 42)
        assert result["ok"] is True
        db.remove_track_from_playlist.assert_called_once_with(1, 42)

    def test_remove_track_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.removeTrackFromPlaylist(1, 42)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_clear_playlist(self):
        db = MagicMock()
        db.clear_playlist.return_value = True
        bridge = PlaylistsBridge(db=db)
        bridge._playlists = [{"id": 1, "title": "Test"}]
        result = bridge.clearPlaylist(1)
        assert result["ok"] is True

    def test_clear_playlist_no_db(self):
        bridge = PlaylistsBridge()
        result = bridge.clearPlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_DB"

    def test_bridge_refresh(self):
        db = MagicMock()
        db.get_playlists.return_value = [
            {"id": 1, "name": "Test", "track_count": 5}
        ]
        bridge = PlaylistsBridge(db=db)
        bridge.refresh()
        assert len(bridge.playlists) == 1
        assert bridge.playlists[0]["title"] == "Test"

    def test_bridge_refresh_empty(self):
        bridge = PlaylistsBridge()
        bridge.refresh()
        assert bridge.playlists == []

    def test_playlist_duration_format(self):
        assert PlaylistsBridge._format_duration(0) == ""
        assert PlaylistsBridge._format_duration(180) == "3 min"
        assert PlaylistsBridge._format_duration(7200) == "2h 0m"
        assert PlaylistsBridge._format_duration(3661) == "1h 1m"
