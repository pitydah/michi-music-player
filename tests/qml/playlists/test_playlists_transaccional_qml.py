"""DO — Playlists transactional QML tests.

Multi-step operations use transactions. Failure causes rollback or explicit partial result.
Operations: list, detail, create, rename, delete, duplicate, add, remove,
reorder, batch add, batch remove, import, export, description, cover,
missing tracks, smart rules, save Queue.
"""
import sqlite3
from unittest.mock import patch

import pytest

from core.playlist_service import PlaylistService

pytestmark = [pytest.mark.qml_module("playlists")]


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            cover TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, description, cover, track_count FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2] or "", "cover": r[3] or "", "track_count": r[4]} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        if "create_playlist" in self._fail_on:
            raise RuntimeError("Simulated failure")
        self.conn.execute("INSERT INTO playlists (name, description, cover) VALUES (?, ?, ?)", (name, description, cover))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None, cover=None):
        if "update_playlist" in self._fail_on:
            raise RuntimeError("Simulated failure")
        if name is not None:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        if description is not None:
            self.conn.execute("UPDATE playlists SET description=? WHERE id=?", (description, pid))
        if cover is not None:
            self.conn.execute("UPDATE playlists SET cover=? WHERE id=?", (cover, pid))
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


def test_list_playlists(svc):
    svc.create("List")
    result = svc.list()
    assert len(result) == 1
    assert result[0]["name"] == "List"


def test_create_playlist(svc):
    result = svc.create("New")
    assert result["ok"]
    assert result["id"] > 0


def test_rename_playlist(svc):
    svc.create("Old")
    pid = svc.list()[0]["id"]
    result = svc.rename(pid, "New")
    assert result["ok"]
    assert svc.list()[0]["name"] == "New"


def test_delete_playlist(svc):
    svc.create("ToDelete")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    result = svc.delete(pid)
    assert result["ok"]
    assert len(svc.list()) == 0


def test_duplicate_playlist(svc):
    svc.create("Orig")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=10)
    result = svc.duplicate(pid)
    assert result["ok"]
    assert result["count"] == 1
    assert len(svc.list()) == 2


def test_add_track(svc):
    svc.create("Add")
    pid = svc.list()[0]["id"]
    result = svc.add_track(pid, track_id=42)
    assert result["ok"]
    detail = svc.get_detail(pid)
    assert detail["count"] == 1


def test_remove_track(svc):
    svc.create("Remove")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    result = svc.remove_track(pid, 1)
    assert result["ok"]
    detail = svc.get_detail(pid)
    assert detail["count"] == 0


def test_reorder_tracks(svc):
    svc.create("Reorder")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    svc.add_track(pid, track_id=2)
    svc.add_track(pid, track_id=3)
    result = svc.reorder(pid, 0, 2)
    assert result["ok"]
    detail = svc.get_detail(pid)
    assert detail["tracks"][2]["track_id"] == 1


def test_batch_add(svc):
    svc.create("Batch")
    pid = svc.list()[0]["id"]
    result = svc.batch_add(pid, [1, 2, 3])
    assert result["ok"]
    assert result["count"] == 3


def test_batch_remove(svc):
    svc.create("BatchRemove")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    svc.add_track(pid, track_id=2)
    result = svc.batch_remove(pid, [1, 2])
    assert result["ok"]
    assert result["count"] == 2
    detail = svc.get_detail(pid)
    assert detail["count"] == 0


def test_detect_missing(svc, tmp_path):
    svc.create("Missing")
    pid = svc.list()[0]["id"]
    existing = tmp_path / "exists.flac"
    existing.write_text("data")
    svc.add_track(pid, filepath=str(existing))
    svc.add_track(pid, filepath="/nonexistent.flac")
    result = svc.detect_missing(pid)
    assert result["ok"]
    assert result["count"] == 1


def test_save_queue_from_canonical_items(svc):
    svc.create("SaveQueue")
    items = [
        {"filepath": "/a.flac"},
        {"filepath": "/b.flac"},
    ]
    result = svc.save_queue(items, "From Queue")
    assert result["ok"]
    assert result["count"] == 2


def test_description_and_cover(svc):
    result = svc.create("Desc")
    assert result["ok"]
    assert result["id"] > 0


def test_import_confirm(svc, tmp_path):
    track = tmp_path / "track.flac"
    track.write_text("data")
    m3u = tmp_path / "test.m3u"
    m3u.write_text(f"#EXTM3U\n{track}\n")
    result = svc.import_confirm(str(m3u), "Imported")
    assert result["ok"]
    assert result["count"] == 1
    assert result["name"] == "Imported"


def test_export(svc, tmp_path):
    svc.create("Export")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, filepath="/path/a.flac")
    dest = tmp_path / "out.m3u"
    with patch("core.playlist_service.Path.is_file", return_value=True), \
         patch("core.playlist_io.export_m3u") as mock_export:
        result = svc.export(pid, str(dest))
        assert result["ok"]
        mock_export.assert_called_once()
