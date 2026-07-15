"""Workflow test: create → add → reorder → export via PlaylistsBridge."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists"), pytest.mark.qml_workflow("playlists")]


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.create_playlist.return_value = 1
    db.add_track_to_playlist.return_value = True
    db.reorder_playlist_track.return_value = True
    db.get_playlist_items.return_value = [
        MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                  title="Song 1", artist="Artist A", album="Album X", duration=200),
        MagicMock(id=2, track_uid="u2", filepath="/m/s2.mp3",
                  title="Song 2", artist="Artist B", album="Album Y", duration=180),
        MagicMock(id=3, track_uid="u3", filepath="/m/s3.mp3",
                  title="Song 3", artist="Artist A", album="Album X", duration=240),
    ]
    db.get_playlists.return_value = [
        {"id": 1, "name": "Test Playlist", "track_count": 3}
    ]
    db.update_playlist.return_value = True
    db.delete_playlist.return_value = True
    return db


@pytest.fixture
def player():
    p = MagicMock()
    p.enqueue.return_value = True
    return p


@pytest.fixture
def bridge(mock_db, player):
    b = PlaylistsBridge(db=mock_db, player_service=player)
    b.refresh()
    return b


class TestPlaylistsWorkflow:

    def test_wf_create_playlist(self, bridge):
        result = bridge.createPlaylist("My Playlist")
        assert result["ok"] is True
        assert result["id"] == 1

    def test_wf_add_track(self, bridge):
        result = bridge.addTrackToPlaylist(1, track_id="42")
        assert result["ok"] is True

    def test_wf_add_multiple_tracks(self, bridge):
        result = bridge.batchAddTrackIds(1, [10, 20, 30])
        assert result["ok"] is True
        assert result["count"] == 3

    def test_wf_reorder_tracks(self, bridge):
        result = bridge.reorderTrack(1, 0, 2)
        assert result["ok"] is True

    def test_wf_export_m3u(self, bridge):
        svc = MagicMock()
        svc.export.return_value = {"ok": True, "count": 3}
        bridge._svc = svc
        result = bridge.exportM3U(1, "/tmp/test.m3u")
        assert result["ok"] is True
        assert result["count"] == 3

    def test_wf_full_cycle(self, bridge):
        create_result = bridge.createPlaylist("Full Cycle")
        assert create_result["ok"] is True
        bridge.addTrackToPlaylist(1, track_id="10")
        bridge.addTrackToPlaylist(1, track_id="20")
        bridge.addTrackToPlaylist(1, track_id="30")
        bridge.reorderTrack(1, 2, 0)
        detail = bridge.getPlaylistDetail(1)
        assert detail["ok"] is True
        assert detail["count"] == 3

    def test_wf_play_after_create_and_add(self, bridge):
        result = bridge.playPlaylist(1)
        assert result["ok"] is True
        assert result["count"] == 3

    def test_wf_play_from_index(self, bridge):
        result = bridge.playPlaylistFromIndex(1, 1)
        assert result["ok"] is True

    def test_wf_rename_after_create(self, bridge):
        result = bridge.renamePlaylist(1, "Renamed Playlist")
        assert result["ok"] is True

    def test_wf_duplicate_after_create(self, bridge):
        result = bridge.duplicatePlaylist(1)
        assert result["ok"] is True
        assert "copia" in result["name"]

    def test_wf_clear_then_refill(self, bridge):
        result = bridge.clearPlaylist(1)
        assert result["ok"] is True
        bridge.addTrackToPlaylist(1, track_id="99")
        detail = bridge.getPlaylistDetail(1)
        assert detail["ok"] is True

    def test_wf_delete_playlist(self, bridge):
        result = bridge.deletePlaylist(1)
        assert result["ok"] is True
        bridge.refresh()
        assert len(bridge.playlists) == 0

    def test_wf_playlist_score_after_actions(self, bridge):
        result = bridge.playlistScore()
        assert result["score"] > 0
        assert result["has_db"] is True
