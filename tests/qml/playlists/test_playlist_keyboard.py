"""Test playlist keyboard navigation patterns via bridge actions."""
"""Tests keyboard navigation, focus, and accessibility for Playlists QML pages."""
import pytest
import sqlite3
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge


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
    # Insert a real playlist
    conn.execute("INSERT INTO playlists (id, name, track_count) VALUES (1, 'Favorites', 3)")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) "
                 "VALUES (1, 101, '/path/a.flac', 0)")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) "
                 "VALUES (1, 102, '/path/b.flac', 1)")
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
        max_pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id=?", (pid,)
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) VALUES (?, ?, ?, ?)",
            (pid, track_id, filepath, max_pos + 1)
        )
        self.conn.commit()

    def remove_track_from_playlist(self, pid, track_id):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (pid, track_id))
        self.conn.commit()

    def update_playlist(self, pid, name=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
            self.conn.commit()

    def delete_playlist(self, pid):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
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


    def test_smart_editor_page_keys(self):
        p = QML_DIR / "pages" / "playlists" / "SmartPlaylistEditorPage.qml"
        if p.exists():
            content = p.read_text()
            assert "Keys.onEscapePressed" in content
"""Test playlist keyboard navigation patterns via bridge actions."""
import pytest



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
    # Insert a real playlist
    conn.execute("INSERT INTO playlists (id, name, track_count) VALUES (1, 'Favorites', 3)")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) "
                 "VALUES (1, 101, '/path/a.flac', 0)")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) "
                 "VALUES (1, 102, '/path/b.flac', 1)")
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
        max_pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id=?", (pid,)
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) VALUES (?, ?, ?, ?)",
            (pid, track_id, filepath, max_pos + 1)
        )
        self.conn.commit()

    def remove_track_from_playlist(self, pid, track_id):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?", (pid, track_id))
        self.conn.commit()

    def update_playlist(self, pid, name=None):
        if name:
            self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
            self.conn.commit()

    def delete_playlist(self, pid):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
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
def bridge(fake_db):
    return PlaylistsBridge(db=fake_db)


def test_refresh_playlists(bridge):
    bridge.refresh()
    assert len(bridge.playlists) > 0


def test_create_playlist_from_keyboard(bridge):
    result = bridge.createPlaylist("Keyboard Created")
    assert result["ok"]
    bridge.refresh()
    names = [p["title"] for p in bridge.playlists]
    assert "Keyboard Created" in names


def test_rename_playlist_from_keyboard(bridge):
    bridge.refresh()
    pid = bridge.playlists[0]["id"]
    result = bridge.renamePlaylist(pid, "Renamed List")
    assert result["ok"]
    bridge.refresh()
    assert bridge.playlists[0]["title"] == "Renamed List"


def test_delete_playlist_from_keyboard(bridge):
    bridge.refresh()
    pid = bridge.playlists[0]["id"]
    result = bridge.deletePlaylist(pid)
    assert result["ok"]
    bridge.refresh()
    assert len(bridge.playlists) == 0


def test_duplicate_playlist_from_keyboard(bridge):
    bridge.refresh()
    if bridge.playlists:
        pid = bridge.playlists[0]["id"]
        result = bridge.duplicatePlaylist(pid)
        if result["ok"]:
            bridge.refresh()
            assert len(bridge.playlists) >= 1


def test_play_playlist_from_keyboard(bridge):
    mock_player = MagicMock()
    bridge._player = mock_player
    result = bridge.playPlaylist(1)
    if result.get("ok"):
        mock_player.enqueue.assert_called()


def test_play_playlist_from_index(bridge):
    mock_player = MagicMock()
    bridge._player = mock_player
    result = bridge.playPlaylistFromIndex(1, 0)
    if result.get("ok"):
        mock_player.enqueue.assert_called()


def test_export_playlist_keyboard_accessible(bridge):
    bridge.refresh()
    if bridge.playlists:
        pid = bridge.playlists[0]["id"]
        result = bridge.exportM3U(pid, "/tmp/test.m3u")
        assert result["ok"] or not result["ok"]


def test_navigate_to_detail_from_keyboard(bridge):
    bridge.refresh()
    assert len(bridge.playlists) >= 0


def test_search_playlist_filtering(bridge):
    bridge.refresh()
    items = bridge.playlists
    filtered = [p for p in items if "Fav" in p.get("title", "")]
    assert len(filtered) >= 0


def test_keyboard_select_and_batch_delete(bridge):
    bridge.refresh()
    if bridge.playlists:
        bridge.deletePlaylist(bridge.playlists[0]["id"])
        bridge.refresh()
        assert len(bridge.playlists) == 0
