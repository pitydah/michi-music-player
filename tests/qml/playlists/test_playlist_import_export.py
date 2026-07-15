"""Test playlist import/export: M3U, preview, confirm, cancel, missing detection."""
import pytest
import sqlite3
from unittest.mock import patch

from core.playlist_service import PlaylistService
pytestmark = [pytest.mark.qml_module("playlists")]



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

    def get_playlists(self):
        rows = self.conn.execute("SELECT id, name, track_count FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2]} for r in rows]

    def create_playlist(self, name):
        self.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

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


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


def test_import_preview_m3u(svc, tmp_path):
    m3u = tmp_path / "test.m3u"
    m3u.write_text("#EXTM3U\n/path/to/track1.flac\n/path/to/track2.flac\n")
    result = svc.import_preview(str(m3u))
    assert result["ok"]
    assert result["total_entries"] == 2


def test_import_preview_file_not_found(svc):
    result = svc.import_preview("/nonexistent/file.m3u")
    assert not result["ok"]
    assert result["error_code"] == "FILE_NOT_FOUND"


def test_import_preview_empty_file(svc, tmp_path):
    m3u = tmp_path / "empty.m3u"
    m3u.write_text("")
    result = svc.import_preview(str(m3u))
    assert result["ok"]


def test_import_confirm_valid(svc, tmp_path):
    track = tmp_path / "track.flac"
    track.write_text("data")
    m3u = tmp_path / "test.m3u"
    m3u.write_text(f"#EXTM3U\n{track}\n")
    result = svc.import_confirm(str(m3u), "Imported")
    assert result["ok"]
    assert result["count"] == 1
    assert result["name"] == "Imported"


def test_import_confirm_no_name_uses_stem(svc, tmp_path):
    track = tmp_path / "track.flac"
    track.write_text("data")
    m3u = tmp_path / "mylist.m3u"
    m3u.write_text(f"#EXTM3U\n{track}\n")
    result = svc.import_confirm(str(m3u))
    assert result["ok"]
    assert result["name"] == "mylist"


def test_import_confirm_no_db(svc):
    svc_no_db = PlaylistService(db=None)
    result = svc_no_db.import_confirm("/path/to/file.m3u")
    assert not result["ok"]


def test_export_m3u(svc, tmp_path):
    svc.create("Export")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, track_id=1, filepath="/path/1.flac")
    dest = tmp_path / "export.m3u"
    with patch("core.playlist_service.Path.is_file", return_value=True), \
         patch("ui.playlist_io.export_m3u") as mock_export:
        result = svc.export(pid, str(dest))
        assert result["ok"]
        mock_export.assert_called_once()


def test_export_empty_path(svc):
    svc.create("ExportEmpty")
    pid = svc.list()[0]["id"]
    result = svc.export(pid, "")
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_PATH"


def test_cancel_import(svc):
    result = svc.cancel_import("import_123")
    assert result["ok"]
    assert result["cancelled"] is True
