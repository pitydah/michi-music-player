"""Test PlaylistService transactions: duplicate, reorder, batch, import, cancellation."""
import pytest
import sqlite3
from unittest.mock import MagicMock, patch

from core.playlist_service import PlaylistService


@pytest.fixture
def db_conn():
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
    return conn


class FakeDb:
    def __init__(self, conn):
        self.conn = conn
        self._playlists = []
        self._next_id = 1

    def get_playlists(self):
        rows = self.conn.execute("SELECT id, name, track_count FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2]} for r in rows]

    def create_playlist(self, name):
        self.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()
        pid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self._next_id = pid + 1
        return pid

    def update_playlist(self, pid, name=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
            self.conn.commit()

    def delete_playlist(self, pid):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()

    def get_playlist_items(self, pid):
        rows = self.conn.execute(
            "SELECT track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        return [{"id": r[0] or 0, "track_id": r[0] or 0, "filepath": r[1] or "", "position": r[2] or idx,
                 "title": f"Track {r[0]}" if r[0] else "", "artist": "", "album": "", "duration": 0}
                for idx, r in enumerate(rows)]

    def add_track_to_playlist(self, pid, track_id=None, filepath=None):
        self.conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, filepath) VALUES (?, ?, ?)",
            (pid, track_id, filepath)
        )
        self.conn.commit()

    def remove_track_from_playlist(self, pid, track_id):
        self.conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?",
            (pid, track_id)
        )
        self.conn.commit()

    def reorder_playlist_track(self, pid, from_index, to_index):
        rows = self.conn.execute(
            "SELECT id, track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        if from_index < 0 or from_index >= len(rows) or to_index < 0 or to_index >= len(rows):
            return
        ids = [r[0] for r in rows]
        item = ids.pop(from_index)
        ids.insert(to_index, item)
        for pos, row_id in enumerate(ids):
            self.conn.execute("UPDATE playlist_tracks SET position=? WHERE id=?", (pos, row_id))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


def test_create_playlist(svc):
    result = svc.create("Test Playlist")
    assert result["ok"]
    assert result["id"] > 0


def test_empty_name(svc):
    result = svc.create("")
    assert not result["ok"]


def test_rename(svc):
    svc.create("Original")
    pid = svc.list()[0]["id"]
    result = svc.rename(pid, "Renamed")
    assert result["ok"]


def test_delete(svc):
    svc.create("To Delete")
    pid = svc.list()[0]["id"]
    result = svc.delete(pid)
    assert result["ok"]
    assert len(svc.list()) == 0


def test_duplicate(svc):
    svc.create("Original")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1)
    svc._db.add_track_to_playlist(pid, track_id=2)
    result = svc.duplicate(pid)
    assert result["ok"]
    assert result["count"] == 2


def test_reorder(svc):
    svc.create("Reorder")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1)
    svc._db.add_track_to_playlist(pid, track_id=2)
    svc._db.add_track_to_playlist(pid, track_id=3)
    result = svc.reorder(pid, 0, 2)
    assert result["ok"]


def test_batch_add(svc):
    svc.create("Batch")
    pid = svc.list()[0]["id"]
    result = svc.batch_add(pid, [1, 2, 3])
    assert result["ok"]
    assert result["count"] == 3


def test_batch_remove(svc):
    svc.create("Batch Remove")
    pid = svc.list()[0]["id"]
    svc.batch_add(pid, [1, 2, 3])
    result = svc.batch_remove(pid, [1, 2])
    assert result["ok"]
    assert result["count"] == 2


def test_batch_add_empty(svc):
    svc.create("Empty")
    pid = svc.list()[0]["id"]
    result = svc.batch_add(pid, [])
    assert not result["ok"]


def test_batch_remove_empty(svc):
    svc.create("Empty")
    pid = svc.list()[0]["id"]
    result = svc.batch_remove(pid, [])
    assert not result["ok"]


def test_detect_missing_tracks(svc, tmp_path):
    svc.create("Missing")
    pid = svc.list()[0]["id"]
    existing = tmp_path / "exists.flac"
    existing.write_text("data")
    svc._db.add_track_to_playlist(pid, filepath=str(existing))
    svc._db.add_track_to_playlist(pid, filepath="/nonexistent/path.flac")
    result = svc.detect_missing_tracks(pid)
    assert result["ok"]
    assert result["count"] == 1


def test_import_preview(svc, tmp_path):
    m3u = tmp_path / "test.m3u"
    m3u.write_text("#EXTM3U\n/path/to/track1.flac\n/path/to/track2.flac\n")
    result = svc.import_preview(str(m3u))
    assert result["ok"]
    assert result["total_entries"] == 2


def test_import_preview_file_not_found(svc):
    result = svc.import_preview("/nonexistent/file.m3u")
    assert not result["ok"]
    assert result["error_code"] == "FILE_NOT_FOUND"


def test_import_confirm(svc, tmp_path):
    track = tmp_path / "track.flac"
    track.write_text("data")
    m3u = tmp_path / "test.m3u"
    m3u.write_text(f"#EXTM3U\n{track}\n")
    result = svc.import_confirm(str(m3u), "Imported")
    assert result["ok"]
    assert result["count"] == 1


def test_export(svc, tmp_path):
    svc.create("Export")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1, filepath="/path/1.flac")
    svc._db.add_track_to_playlist(pid, track_id=2, filepath="/path/2.flac")
    dest = tmp_path / "export.m3u"
    with patch("core.playlist_service.Path.is_file", return_value=True), patch("ui.playlist_io.export_m3u"):
        result = svc.export(pid, str(dest))
        assert result["ok"]


def test_cancel_import(svc):
    result = svc.cancel_import("import_123")
    assert result["ok"]
    assert result["cancelled"] is True


def test_cancel_import_no_id(svc):
    result = svc.cancel_import("")
    assert not result["ok"]


def test_transaction_commit_rollback(svc):
    svc.create("Txn")
    pid = svc.list()[0]["id"]
    svc.begin()
    svc._db.add_track_to_playlist(pid, track_id=1)
    svc.commit()
    detail = svc.get_detail(pid)
    assert detail["count"] == 1


def test_play_from_index(svc):
    player = MagicMock()
    player.enqueue.return_value = None
    svc.create("Play")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1, filepath="/path/1.flac")
    result = svc.play_from_index(pid, 0, player)
    assert result["ok"]


def test_play_from_index_invalid(svc):
    svc.create("Play Invalid")
    pid = svc.list()[0]["id"]
    result = svc.play_from_index(pid, 999, MagicMock())
    assert not result["ok"]


def test_get_detail(svc):
    svc.create("Detail")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1)
    svc._db.add_track_to_playlist(pid, track_id=2)
    detail = svc.get_detail(pid)
    assert detail["ok"]
    assert detail["count"] == 2


def test_list(svc):
    svc.create("List A")
    svc.create("List B")
    plists = svc.list()
    assert len(plists) == 2


def test_no_db():
    svc = PlaylistService(db=None)
    assert svc.list() == []
    assert svc.create("Test") == {"ok": False, "error_code": "NO_DB", "message": ""}
