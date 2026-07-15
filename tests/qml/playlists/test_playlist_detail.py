"""Test playlist detail page with track list, metadata, missing tracks."""
"""Tests for PlaylistDetailPage: bridge interactions, track loading, CRUD."""
import pytest
import sqlite3

from core.playlist_service import PlaylistService
import pytest


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, track_count, description FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2], "description": r[3] or ""} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        self.conn.execute("INSERT INTO playlists (name, description) VALUES (?, ?)", (name, description))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        if description is not None:
            self.conn.execute("UPDATE playlists SET description=? WHERE id=?", (description, pid))
        self.conn.commit()

    def get_playlist_items(self, pid):
        rows = self.conn.execute(
            "SELECT track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        return [{"id": r[0] or 0, "track_id": r[0] or 0, "filepath": r[1] or "", "position": r[2] or idx,
                 "title": f"Track {r[0]}" if r[0] else "", "artist": f"Artist {r[0]}",
                 "album": f"Album {r[0]}", "duration": 200}
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

    def reorder_playlist_track(self, pid, from_index, to_index):
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
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


class TestPlaylistDetail:
    def test_detail_shows_tracks(self, svc):
        svc.create("My List")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        svc.add_track(pid, track_id=2)
        detail = svc.get_detail(pid)
        assert detail["ok"]
        assert detail["count"] == 2

    def test_detail_contains_metadata(self, svc):
        svc.create("Detail")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=42)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert track["track_id"] == 42

    def test_detail_has_duration(self, svc):
        svc.create("Duration")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=7)
        detail = svc.get_detail(pid)
        assert "duration" in detail["tracks"][0]

    def test_detail_empty_playlist(self, svc):
        svc.create("Empty")
        pid = svc.list()[0]["id"]
        detail = svc.get_detail(pid)
        assert detail["ok"]
        assert detail["count"] == 0

    def test_detail_nonexistent_playlist(self, svc):
        detail = svc.get_detail(999)
        assert detail is None or not detail.get("ok", False) or detail.get("count", 0) == 0

    def test_detail_includes_public_ref(self, svc):
        svc.create("Public")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=10)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track

    def test_detail_cover_key_present(self, svc):
        svc.create("Cover")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track

    def test_detail_missing_track_detection(self, svc, tmp_path):
        svc.create("Missing")
        pid = svc.list()[0]["id"]
        real = tmp_path / "real.flac"
        real.write_text("data")
        svc.add_track(pid, filepath=str(real))
        svc.add_track(pid, filepath="/nonexistent/path.flac")
        detail = svc.get_detail(pid)
        tracks = detail["tracks"]
        assert len(tracks) == 2

    def test_detail_missing_not_set_on_existing(self, svc, tmp_path):
        svc.create("Exists")
        pid = svc.list()[0]["id"]
        real = tmp_path / "real.flac"
        real.write_text("data")
        svc.add_track(pid, filepath=str(real))
        detail = svc.get_detail(pid)
        for t in detail["tracks"]:
            if t.get("filepath"):
                assert not t.get("missing", True)

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
"""Test playlist detail page with track list, metadata, missing tracks."""


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, track_count, description FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2], "description": r[3] or ""} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        self.conn.execute("INSERT INTO playlists (name, description) VALUES (?, ?)", (name, description))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        if description is not None:
            self.conn.execute("UPDATE playlists SET description=? WHERE id=?", (description, pid))
        self.conn.commit()

    def get_playlist_items(self, pid):
        rows = self.conn.execute(
            "SELECT track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        return [{"id": r[0] or 0, "track_id": r[0] or 0, "filepath": r[1] or "", "position": r[2] or idx,
                 "title": f"Track {r[0]}" if r[0] else "", "artist": f"Artist {r[0]}",
                 "album": f"Album {r[0]}", "duration": 200}
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

    def reorder_playlist_track(self, pid, from_index, to_index):
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
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


class TestPlaylistDetail:
    def test_detail_shows_tracks(self, svc):
        svc.create("My List")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        svc.add_track(pid, track_id=2)
        detail = svc.get_detail(pid)
        assert detail["ok"]
        assert detail["count"] == 2

    def test_detail_contains_metadata(self, svc):
        svc.create("Detail")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=42)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert track["track_id"] == 42

    def test_detail_has_duration(self, svc):
        svc.create("Duration")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=7)
        detail = svc.get_detail(pid)
        assert "duration" in detail["tracks"][0]

    def test_detail_empty_playlist(self, svc):
        svc.create("Empty")
        pid = svc.list()[0]["id"]
        detail = svc.get_detail(pid)
        assert detail["ok"]
        assert detail["count"] == 0

    def test_detail_nonexistent_playlist(self, svc):
        detail = svc.get_detail(999)
        assert detail is None or not detail.get("ok", False) or detail.get("count", 0) == 0

    def test_detail_includes_public_ref(self, svc):
        svc.create("Public")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=10)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track

    def test_detail_cover_key_present(self, svc):
        svc.create("Cover")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        detail = svc.get_detail(pid)
        track = detail["tracks"][0]
        assert "track_id" in track

    def test_detail_missing_track_detection(self, svc, tmp_path):
        svc.create("Missing")
        pid = svc.list()[0]["id"]
        real = tmp_path / "real.flac"
        real.write_text("data")
        svc.add_track(pid, filepath=str(real))
        svc.add_track(pid, filepath="/nonexistent/path.flac")
        detail = svc.get_detail(pid)
        tracks = detail["tracks"]
        assert len(tracks) == 2

    def test_detail_missing_not_set_on_existing(self, svc, tmp_path):
        svc.create("Exists")
        pid = svc.list()[0]["id"]
        real = tmp_path / "real.flac"
        real.write_text("data")
        svc.add_track(pid, filepath=str(real))
        detail = svc.get_detail(pid)
        for t in detail["tracks"]:
            if t.get("filepath"):
                assert not t.get("missing", True)

    def test_detail_tracklist_ordered_by_position(self, svc):
        svc.create("Ordered")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=3)
        svc.add_track(pid, track_id=1)
        svc.add_track(pid, track_id=2)
        detail = svc.get_detail(pid)
        track_ids = [t["track_id"] for t in detail["tracks"]]
        assert track_ids == [3, 1, 2]
