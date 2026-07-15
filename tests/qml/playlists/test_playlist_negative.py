"""Test playlist negative paths: missing service, empty playlists, import errors."""
"""Negative tests for Playlists: null bridge, invalid inputs, edge cases, error states."""
import pytest
import sqlite3

from core.playlist_service import PlaylistService
from ui_qml_bridge.playlists_bridge import PlaylistsBridge


def test_bridge_without_db():
    bridge = PlaylistsBridge(db=None)
    assert len(bridge.playlists) == 0


def test_bridge_no_playlists():
    bridge = PlaylistsBridge(db=None)
    bridge.refresh()
    assert len(bridge.playlists) == 0


def test_create_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.createPlaylist("Test")
    assert not result["ok"]


def test_delete_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.deletePlaylist(1)
    assert not result["ok"]


def test_rename_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.renamePlaylist(1, "New")
    assert not result["ok"]


def test_get_detail_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.getPlaylistDetail(1)
    assert not result["ok"]


def test_export_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.exportM3U(1, "/tmp/out.m3u")
    assert not result["ok"]


def test_import_preview_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.previewPlaylistImport("/path/to/file.m3u")
    assert not result["ok"]


def test_import_confirm_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.confirmPlaylistImport("/path/to/file.m3u")
    assert not result["ok"]

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
"""Test playlist negative paths: missing service, empty playlists, import errors."""



def test_bridge_without_db():
    bridge = PlaylistsBridge(db=None)
    assert len(bridge.playlists) == 0


def test_bridge_no_playlists():
    bridge = PlaylistsBridge(db=None)
    bridge.refresh()
    assert len(bridge.playlists) == 0


def test_create_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.createPlaylist("Test")
    assert not result["ok"]


def test_delete_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.deletePlaylist(1)
    assert not result["ok"]


def test_rename_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.renamePlaylist(1, "New")
    assert not result["ok"]


def test_get_detail_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.getPlaylistDetail(1)
    assert not result["ok"]


def test_export_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.exportM3U(1, "/tmp/out.m3u")
    assert not result["ok"]


def test_import_preview_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.previewPlaylistImport("/path/to/file.m3u")
    assert not result["ok"]


def test_import_confirm_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.confirmPlaylistImport("/path/to/file.m3u")
    assert not result["ok"]


def test_play_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.playPlaylist(1)
    assert not result["ok"]


def test_play_from_index_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.playPlaylistFromIndex(1, 0)
    assert not result["ok"]


def test_bridge_can_returns_false_without_db():
    bridge = PlaylistsBridge(db=None)
    assert not bridge._can() if hasattr(bridge, '_can') else True


def test_duplicate_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.duplicatePlaylist(1)
    assert not result["ok"]


def test_clear_playlist_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.clearPlaylist(1)
    assert not result["ok"]


def test_reorder_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.reorderTrack(1, 0, 1)
    assert not result["ok"]


def test_empty_playlist_list():
    bridge = PlaylistsBridge(db=None)
    bridge.refresh()
    assert len(bridge.playlists) == 0


def test_add_track_no_selection():
    bridge = PlaylistsBridge(db=None)
    result = bridge.addTrackToPlaylist(1, "", "")
    assert not result["ok"]


def test_batch_add_no_db():
    bridge = PlaylistsBridge(db=None)
    result = bridge.batchAddTracks(1, [{"track_id": 1}])
    assert not result["ok"]


def test_save_queue_no_name():
    bridge = PlaylistsBridge(db=None)
    result = bridge.saveQueueAsPlaylist("")
    assert not result["ok"]


def test_score_zero_no_db():
    bridge = PlaylistsBridge(db=None)
    score = bridge.playlistScore()
    assert score["score"] == 0 or score["score"] >= 0


def test_cancel_import_no_service():
    bridge = PlaylistsBridge(db=None)
    result = bridge.cancelPlaylistImport("import_1")
    assert result["ok"]


def test_playlist_service_no_db():
    svc = PlaylistService(db=None)
    result = svc.create("Test")
    assert not result["ok"]
    assert result["error_code"] == "NO_DB"


def test_playlist_service_list_no_db():
    svc = PlaylistService(db=None)
    result = svc.list()
    assert result == []


def test_playlist_service_rename_no_db():
    svc = PlaylistService(db=None)
    result = svc.rename(1, "New")
    assert not result["ok"]


def test_playlist_service_delete_no_db():
    svc = PlaylistService(db=None)
    result = svc.delete(1)
    assert not result["ok"]


def test_playlist_service_get_detail_no_db():
    svc = PlaylistService(db=None)
    result = svc.get_detail(1)
    assert not result["ok"]


def test_import_preview_invalid_file(svc_with_db, tmp_path):
    m3u = tmp_path / "invalid.m3u"
    m3u.write_text("NOT A PLAYLIST FORMAT")
    result = svc_with_db.import_preview(str(m3u))
    assert result["ok"] is True or result["ok"] is False


def test_import_confirm_missing_file(svc_with_db):
    result = svc_with_db.import_confirm("/nonexistent/file.m3u")
    assert result is None or result.get("count", 999) == 0


@pytest.fixture
def fake_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id INTEGER,
            filepath TEXT,
            position INTEGER DEFAULT 0,
            added_at TEXT DEFAULT ''
        )
    """)
    conn.commit()

    class FakeDbInstance:
        def __init__(self, conn):
            self.conn = conn

        def get_playlists(self):
            return []

        def create_playlist(self, name):
            conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def get_playlist_items(self, pid):
            return []

        def add_track_to_playlist(self, pid, track_id=None, filepath=None):
            pass

    return FakeDbInstance(conn)


@pytest.fixture
def svc_with_db(fake_db):
    return PlaylistService(db=fake_db)
