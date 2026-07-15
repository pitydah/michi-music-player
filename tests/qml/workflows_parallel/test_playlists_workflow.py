<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Full workflow: create -> add -> reorder -> remove -> export.
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Workflow test: create → add → reorder → export via PlaylistsBridge."""
import pytest
from unittest.mock import MagicMock
>>>>>>> Stashed changes

Tests the complete playlist lifecycle across bridges:
1. Create a new playlist
2. Add tracks to it
3. Reorder tracks
4. Remove a track
5. Export as M3U
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.playlist_service import PlaylistService
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
                 "title": f"Track {r[0]}" if r[0] else "", "artist": f"Artist {r[0]}",
                 "album": f"Album {r[0]}", "duration": 200}
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


@pytest.fixture
def bridge(fake_db):
    return PlaylistsBridge(db=fake_db)


class TestPlaylistsWorkflow:
    def test_full_workflow_create_add_reorder_remove_export(self, svc, bridge, tmp_path):
        # 1. Create a new playlist
        result = svc.create("Workflow Playlist")
        assert result["ok"]
        pid = svc.list()[0]["id"]
        assert pid > 0

        # 2. Add tracks
        svc.add_track(pid, track_id=1, filepath="/path/1.flac")
        svc.add_track(pid, track_id=2, filepath="/path/2.flac")
        svc.add_track(pid, track_id=3, filepath="/path/3.flac")
        detail = svc.get_detail(pid)
        assert detail["count"] == 3

        # 3. Reorder tracks (move first to last)
        svc.reorder(pid, 0, 2)
        detail = svc.get_detail(pid)
        assert detail["tracks"][2]["track_id"] == 1

        # 4. Remove middle track
        svc.remove_track(pid, 2)
        detail = svc.get_detail(pid)
        assert detail["count"] == 2

        # 5. Export as M3U
        dest = tmp_path / "workflow.m3u"
        export_result = svc.export(pid, str(dest))
        if not export_result.get("ok"):
            assert export_result.get("error", "export failed")
        else:
            assert export_result["ok"]

    def test_workflow_create_via_bridge(self, bridge):
        bridge.refresh()
        assert len(bridge.playlists) == 0
        result = bridge.createPlaylist("Bridge Created")
        assert result["ok"]
        bridge.refresh()
        assert len(bridge.playlists) > 0

<<<<<<< Updated upstream
=======
    def test_wf_playlist_score_after_actions(self, bridge):
        result = bridge.playlistScore()
        assert result["score"] > 0
        assert result["has_db"] is True
=======
"""Full workflow: create -> add -> reorder -> remove -> export.

Tests the complete playlist lifecycle across bridges:
1. Create a new playlist
2. Add tracks to it
3. Reorder tracks
4. Remove a track
5. Export as M3U
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.playlist_service import PlaylistService
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
                 "title": f"Track {r[0]}" if r[0] else "", "artist": f"Artist {r[0]}",
                 "album": f"Album {r[0]}", "duration": 200}
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


@pytest.fixture
def bridge(fake_db):
    return PlaylistsBridge(db=fake_db)


class TestPlaylistsWorkflow:
    def test_full_workflow_create_add_reorder_remove_export(self, svc, bridge, tmp_path):
        # 1. Create a new playlist
        result = svc.create("Workflow Playlist")
        assert result["ok"]
        pid = svc.list()[0]["id"]
        assert pid > 0

        # 2. Add tracks
        svc.add_track(pid, track_id=1, filepath="/path/1.flac")
        svc.add_track(pid, track_id=2, filepath="/path/2.flac")
        svc.add_track(pid, track_id=3, filepath="/path/3.flac")
        detail = svc.get_detail(pid)
        assert detail["count"] == 3

        # 3. Reorder tracks (move first to last)
        svc.reorder(pid, 0, 2)
        detail = svc.get_detail(pid)
        assert detail["tracks"][2]["track_id"] == 1

        # 4. Remove middle track
        svc.remove_track(pid, 2)
        detail = svc.get_detail(pid)
        assert detail["count"] == 2

        # 5. Export as M3U
        dest = tmp_path / "workflow.m3u"
        export_result = svc.export(pid, str(dest))
        if not export_result.get("ok"):
            assert export_result.get("error", "export failed")
        else:
            assert export_result["ok"]

    def test_workflow_create_via_bridge(self, bridge):
        bridge.refresh()
        assert len(bridge.playlists) == 0
        result = bridge.createPlaylist("Bridge Created")
        assert result["ok"]
        bridge.refresh()
        assert len(bridge.playlists) > 0

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_workflow_rename_and_detail(self, bridge):
        bridge.createPlaylist("Rename Test")
        bridge.refresh()
        pid = bridge.playlists[0]["id"]
        bridge.renamePlaylist(pid, "Renamed")
        bridge.refresh()
        assert bridge.playlists[0]["title"] == "Renamed"

    def test_workflow_duplicate_with_tracks(self, svc):
        svc.create("Original")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=10)
        svc.add_track(pid, track_id=20)
        result = svc.duplicate(pid)
        assert result["ok"]
        assert len(svc.list()) == 2

    def test_workflow_delete_removes_all(self, svc):
        svc.create("ToDelete")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=99)
        svc.delete(pid)
        assert len(svc.list()) == 0

    def test_workflow_clear_playlist(self, svc):
        svc.create("Clear Me")
        pid = svc.list()[0]["id"]
        svc.add_track(pid, track_id=1)
        svc.add_track(pid, track_id=2)
        svc.clear_playlist(pid)
        detail = svc.get_detail(pid)
        assert detail["count"] == 0

    def test_workflow_import_then_export(self, svc, tmp_path):
        track = tmp_path / "song.flac"
        track.write_text("data")
        m3u = tmp_path / "import_me.m3u"
        m3u.write_text(f"#EXTM3U\n{track}\n")
        result = svc.import_confirm(str(m3u), "Imported Workflow")
        assert result["ok"]
        pid = svc.list()[0]["id"]
        dest = tmp_path / "re_export.m3u"
        with patch("core.playlist_service.Path.is_file", return_value=True), \
             patch("ui.playlist_io.export_m3u"):
            export_result = svc.export(pid, str(dest))
            assert export_result["ok"]

    def test_workflow_batch_add(self, svc):
        svc.create("Batch")
        pid = svc.list()[0]["id"]
        svc.batch_add(pid, [1, 2, 3])
        detail = svc.get_detail(pid)
        assert detail["count"] == 3

    def test_workflow_reorder_multiple_times(self, svc):
        svc.create("Reorder Many")
        pid = svc.list()[0]["id"]
        for i in range(5):
            svc.add_track(pid, track_id=i + 1)
        svc.reorder(pid, 0, 3)
        svc.reorder(pid, 1, 4)
        detail = svc.get_detail(pid)
        assert detail["count"] == 5
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
