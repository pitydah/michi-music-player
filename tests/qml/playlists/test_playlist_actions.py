"""Test playlist CRUD actions: create, rename, duplicate, delete."""
"""Tests for playlist actions: create, rename, duplicate, delete, reorder, add/remove tracks."""
import pytest
import sqlite3

from core.playlist_service import PlaylistService


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            cover TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, track_count, description, cover FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2], "description": r[3] or "",
                 "cover": r[4] or ""} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        self.conn.execute("INSERT INTO playlists (name, description, cover) VALUES (?, ?, ?)",
                          (name, description, cover))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None, cover=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        if description is not None:
            self.conn.execute("UPDATE playlists SET description=? WHERE id=?", (description, pid))
        if cover is not None:
            self.conn.execute("UPDATE playlists SET cover=? WHERE id=?", (cover, pid))
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
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (pid, track_id))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


class TestPlaylistActions:
    def test_create_playlist(self, svc):
        result = svc.create("New Playlist")
        assert result["ok"]
        assert result["name"] == "New Playlist"
        plists = svc.list()
        assert len(plists) == 1

    def test_create_playlist_with_description(self, svc):
        result = svc.create("Desc with desc")
        assert result["ok"]

    def test_create_empty_name_fails(self, svc):
        result = svc.create("")
        assert not result["ok"]
        assert result["error_code"] == "EMPTY_NAME"

    def test_create_duplicate_name_allowed(self, svc):
        svc.create("Same Name")
        result = svc.create("Same Name")
        assert result["ok"]
        assert len(svc.list()) == 2

    def test_rename_playlist(self, svc):
        svc.create("Old Name")
        pid = svc.list()[0]["id"]
        result = svc.rename(pid, "New Name")
        assert result["ok"]
        assert svc.list()[0]["name"] == "New Name"

    def test_rename_empty_name_fails(self, svc):
        svc.create("Test")
        pid = svc.list()[0]["id"]
        result = svc.rename(pid, "")
        assert not result["ok"]

    def test_rename_nonexistent(self, svc):
        result = svc.rename(999, "Name")
        if result:
            assert not result.get("ok", True)

    def test_duplicate_playlist(self, svc):
        svc.create("Original")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        result = svc.duplicate(pid)
        assert result["ok"]
        assert len(svc.list()) == 2

    def test_duplicate_empty_playlist_fails(self, svc):
        svc.create("Empty Dupe")
        pid = svc.list()[0]["id"]
        result = svc.duplicate(pid)
        assert not result["ok"]

    def test_duplicate_nonexistent(self, svc):
        result = svc.duplicate(999)
        assert not result["ok"]

    def test_delete_playlist(self, svc):
        svc.create("To Delete")
        pid = svc.list()[0]["id"]
        result = svc.delete(pid)
        assert result["ok"]
        assert len(svc.list()) == 0

    def test_delete_nonexistent(self, svc):
        result = svc.delete(999)
        if result:
            assert not result.get("ok", True)

    def test_delete_playlist_removes_tracks(self, svc):
        svc.create("With Tracks")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        svc.delete(pid)
        detail = svc.get_detail(pid)
        assert detail is None or detail.get("count", 0) == 0 if detail else True

    def test_list_playlists(self, svc):
        svc.create("A")
        svc.create("B")
        svc.create("C")
        plists = svc.list()
        assert len(plists) == 3

    def test_list_empty(self, svc):
        plists = svc.list()
        assert plists == []

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
"""Test playlist CRUD actions: create, rename, duplicate, delete."""


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            cover TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, track_count, description, cover FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2], "description": r[3] or "",
                 "cover": r[4] or ""} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        self.conn.execute("INSERT INTO playlists (name, description, cover) VALUES (?, ?, ?)",
                          (name, description, cover))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None, cover=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        if description is not None:
            self.conn.execute("UPDATE playlists SET description=? WHERE id=?", (description, pid))
        if cover is not None:
            self.conn.execute("UPDATE playlists SET cover=? WHERE id=?", (cover, pid))
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
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (pid, track_id))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


class TestPlaylistActions:
    def test_create_playlist(self, svc):
        result = svc.create("New Playlist")
        assert result["ok"]
        assert result["name"] == "New Playlist"
        plists = svc.list()
        assert len(plists) == 1

    def test_create_playlist_with_description(self, svc):
        result = svc.create("Desc with desc")
        assert result["ok"]

    def test_create_empty_name_fails(self, svc):
        result = svc.create("")
        assert not result["ok"]
        assert result["error_code"] == "EMPTY_NAME"

    def test_create_duplicate_name_allowed(self, svc):
        svc.create("Same Name")
        result = svc.create("Same Name")
        assert result["ok"]
        assert len(svc.list()) == 2

    def test_rename_playlist(self, svc):
        svc.create("Old Name")
        pid = svc.list()[0]["id"]
        result = svc.rename(pid, "New Name")
        assert result["ok"]
        assert svc.list()[0]["name"] == "New Name"

    def test_rename_empty_name_fails(self, svc):
        svc.create("Test")
        pid = svc.list()[0]["id"]
        result = svc.rename(pid, "")
        assert not result["ok"]

    def test_rename_nonexistent(self, svc):
        result = svc.rename(999, "Name")
        if result:
            assert not result.get("ok", True)

    def test_duplicate_playlist(self, svc):
        svc.create("Original")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        result = svc.duplicate(pid)
        assert result["ok"]
        assert len(svc.list()) == 2

    def test_duplicate_empty_playlist_fails(self, svc):
        svc.create("Empty Dupe")
        pid = svc.list()[0]["id"]
        result = svc.duplicate(pid)
        assert not result["ok"]

    def test_duplicate_nonexistent(self, svc):
        result = svc.duplicate(999)
        assert not result["ok"]

    def test_delete_playlist(self, svc):
        svc.create("To Delete")
        pid = svc.list()[0]["id"]
        result = svc.delete(pid)
        assert result["ok"]
        assert len(svc.list()) == 0

    def test_delete_nonexistent(self, svc):
        result = svc.delete(999)
        if result:
            assert not result.get("ok", True)

    def test_delete_playlist_removes_tracks(self, svc):
        svc.create("With Tracks")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        svc.delete(pid)
        detail = svc.get_detail(pid)
        assert detail is None or detail.get("count", 0) == 0 if detail else True

    def test_list_playlists(self, svc):
        svc.create("A")
        svc.create("B")
        svc.create("C")
        plists = svc.list()
        assert len(plists) == 3

    def test_list_empty(self, svc):
        plists = svc.list()
        assert plists == []

    def test_list_returns_dicts(self, svc):
        svc.create("Test")
        plists = svc.list()
        assert "id" in plists[0]
        assert "name" in plists[0]
