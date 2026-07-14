"""Test PlaylistService with real SQLite: create, add, reorder, duplicate, export/import, delete, rollback."""
import pytest
import sqlite3
from unittest.mock import patch

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
        self._fail_on: list[str] = []

    def set_fail_on(self, methods: list[str]):
        self._fail_on = methods

    def get_playlists(self):
        rows = self.conn.execute("SELECT id, name, track_count FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2]} for r in rows]

    def create_playlist(self, name):
        if "create_playlist" in self._fail_on:
            raise RuntimeError("Simulated failure")
        self.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None):
        if "update_playlist" in self._fail_on:
            raise RuntimeError("Simulated failure")
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
            self.conn.commit()

    def delete_playlist(self, pid):
        if "delete_playlist" in self._fail_on:
            raise RuntimeError("Simulated failure")
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
        if "add_track" in self._fail_on:
            raise RuntimeError("Simulated failure")
        self.conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, filepath) VALUES (?, ?, ?)",
            (pid, track_id, filepath)
        )
        self.conn.commit()

    def remove_track_from_playlist(self, pid, track_id):
        if "remove_track" in self._fail_on:
            raise RuntimeError("Simulated failure")
        self.conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?",
            (pid, track_id)
        )
        self.conn.commit()

    def reorder_playlist_track(self, pid, from_index, to_index):
        if "reorder" in self._fail_on:
            raise RuntimeError("Simulated failure")
        rows = self.conn.execute(
            "SELECT id, track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        if not rows:
            return
        ids = [r[0] for r in rows]
        item = ids.pop(from_index)
        ids.insert(to_index, item)
        for pos, row_id in enumerate(ids):
            self.conn.execute("UPDATE playlist_tracks SET position=? WHERE id=?", (pos, row_id))
        self.conn.commit()

    def clear_playlist(self, pid):
        if "clear" in self._fail_on:
            raise RuntimeError("Simulated failure")
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


def test_create_playlist_persists_in_sql(svc):
    svc.create("Test Playlist")
    plists = svc.list()
    assert len(plists) == 1
    assert plists[0]["name"] == "Test Playlist"
    assert plists[0]["id"] > 0


def test_add_track_and_verify(svc):
    svc.create("My List")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=42)
    detail = svc.get_detail(pid)
    assert detail["ok"]
    assert detail["count"] == 1
    assert detail["tracks"][0]["track_id"] == 42


def test_add_track_by_filepath(svc, tmp_path):
    track = tmp_path / "song.flac"
    track.write_text("data")
    svc.create("File List")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, filepath=str(track))
    detail = svc.get_detail(pid)
    assert detail["count"] == 1


def test_reorder_tracks(svc):
    svc.create("Reorder")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    svc.add_track(pid, track_id=2)
    svc.add_track(pid, track_id=3)
    svc.reorder(pid, 0, 2)
    detail = svc.get_detail(pid)
    assert detail["tracks"][2]["track_id"] == 1


def test_duplicate_playlist(svc):
    svc.create("Original")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=10)
    svc.add_track(pid, track_id=20)
    result = svc.duplicate(pid)
    assert result["ok"]
    plists = svc.list()
    assert len(plists) == 2
    assert result["count"] == 2


def test_delete_playlist_removes_tracks(svc):
    svc.create("ToDelete")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=99)
    svc.delete(pid)
    assert len(svc.list()) == 0


def test_export_m3u(svc, tmp_path):
    svc.create("Export")
    pid = svc.list()[0]["id"]
    svc._db.add_track_to_playlist(pid, filepath="/path/a.flac")
    dest = tmp_path / "out.m3u"
    with patch("core.playlist_service.Path.is_file", return_value=True), \
         patch("ui.playlist_io.export_m3u") as mock_export:
        result = svc.export(pid, str(dest))
        assert result["ok"]
        mock_export.assert_called_once()


def test_import_m3u(svc, tmp_path):
    track = tmp_path / "song.flac"
    track.write_text("data")
    m3u = tmp_path / "import.m3u"
    m3u.write_text(f"#EXTM3U\n{track}\n")
    result = svc.import_confirm(str(m3u), "Imported")
    assert result["ok"]
    assert result["count"] >= 1
    plists = svc.list()
    assert any(p["name"] == "Imported" for p in plists)


def test_rollback_on_partial_add_failure(svc, fake_db):
    svc.create("Partial")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    fake_db.set_fail_on(["add_track"])
    result = svc.add_track(pid, track_id=2)
    assert not result["ok"]
    detail = svc.get_detail(pid)
    assert detail["count"] == 1


def test_rename_playlist(svc):
    svc.create("Old Name")
    pid = svc.list()[0]["id"]
    svc.rename(pid, "New Name")
    assert svc.list()[0]["name"] == "New Name"


def test_clear_playlist(svc):
    svc.create("Clear")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=5)
    svc.add_track(pid, track_id=6)
    svc.clear_playlist(pid)
    detail = svc.get_detail(pid)
    assert detail["count"] == 0


def test_detect_missing_tracks(svc, tmp_path):
    svc.create("Missing")
    pid = svc.list()[0]["id"]
    existing = tmp_path / "real.flac"
    existing.write_text("data")
    svc.add_track(pid, filepath=str(existing))
    svc.add_track(pid, filepath="/nonexistent/path.flac")
    result = svc.detect_missing(pid)
    assert result["ok"]
    assert result["count"] == 1
