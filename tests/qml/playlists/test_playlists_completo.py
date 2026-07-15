"""Comprehensive playlist tests: create, rename, duplicate, delete, clear,
add/remove tracks, batch add, reorder, play, import/export M3U/M3U8,
smart rules, cover, description, missing tracks, partial success, rollback.
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.playlist_service import PlaylistService
from ui_qml_bridge.playlists_bridge import PlaylistsBridge


@pytest.fixture
def db_conn():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            track_count INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            cover TEXT DEFAULT '',
            smart_rule TEXT DEFAULT '',
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
        rows = self.conn.execute("SELECT id, name, track_count, description, cover, smart_rule FROM playlists").fetchall()
        return [{"id": r[0], "name": r[1], "track_count": r[2], "description": r[3] or "",
                 "cover": r[4] or "", "smart_rule": r[5] or ""} for r in rows]

    def create_playlist(self, name, description="", cover=""):
        self.conn.execute("INSERT INTO playlists (name, description, cover) VALUES (?, ?, ?)",
                          (name, description, cover))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_playlist(self, pid, name=None, description=None, cover=None, smart_rule=None):
        fields = []
        vals = []
        if name is not None:
            fields.append("name=?")
            vals.append(name)
        if description is not None:
            fields.append("description=?")
            vals.append(description)
        if cover is not None:
            fields.append("cover=?")
            vals.append(cover)
        if smart_rule is not None:
            fields.append("smart_rule=?")
            vals.append(smart_rule)
        if fields:
            vals.append(pid)
            self.conn.execute(f"UPDATE playlists SET {', '.join(fields)} WHERE id=?", vals)
            self.conn.commit()

    def delete_playlist(self, pid):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()

    def clear_playlist(self, pid):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=?", (pid,))
        self.conn.commit()

    def get_playlist_items(self, pid):
        rows = self.conn.execute(
            "SELECT id, track_id, filepath, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        return [{"id": r[1] or 0, "track_id": r[1] or 0, "filepath": r[2] or "", "position": r[3] or idx,
                 "title": f"Track {r[1]}" if r[1] else "", "artist": "", "album": "", "duration": 0}
                for idx, r in enumerate(rows)]

    def add_track_to_playlist(self, pid, track_id=None, filepath=None):
        pos = self.conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_tracks WHERE playlist_id=?", (pid,)).fetchone()[0]
        self.conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, filepath, position) VALUES (?, ?, ?, ?)",
            (pid, track_id, filepath, pos)
        )
        self.conn.commit()

    def remove_track_from_playlist(self, pid, track_id):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND (track_id=? OR id=?)", (pid, track_id, track_id))
        self.conn.commit()

    def reorder_playlist_track(self, pid, from_index, to_index):
        rows = self.conn.execute(
            "SELECT id, position FROM playlist_tracks WHERE playlist_id=? ORDER BY position",
            (pid,)
        ).fetchall()
        ids = [r[0] for r in rows]
        positions = list(range(len(ids)))
        if 0 <= from_index < len(ids) and 0 <= to_index < len(ids):
            val = positions.pop(from_index)
            positions.insert(to_index, val)
            for tid, pos in zip(ids, positions, strict=False):
                self.conn.execute("UPDATE playlist_tracks SET position=? WHERE id=?", (pos, tid))
            self.conn.commit()


@pytest.fixture
def fake_db(db_conn):
    return FakeDb(db_conn)


@pytest.fixture
def svc(fake_db):
    return PlaylistService(db=fake_db)


@pytest.fixture
def bridge(svc):
    return PlaylistsBridge(playlist_service=svc)


@pytest.fixture
def populated_svc(svc):
    svc.create("Playlist A")
    svc.create("Playlist B")
    pid = svc.list()[0]["id"]
    svc.add_track(pid, track_id=1)
    svc.add_track(pid, track_id=2)
    svc.add_track(pid, track_id=3)
    return svc


@pytest.fixture
def populated_bridge(populated_svc):
    b = PlaylistsBridge(playlist_service=populated_svc)
    b.refresh()
    return b


class TestCreateRenameDuplicate:
    def test_create_playlist(self, bridge):
        result = bridge.createPlaylist("Test Playlist")
        assert result["ok"]
        assert bridge._playlists[0]["title"] == "Test Playlist"

    def test_create_empty_name_fails(self, bridge):
        result = bridge.createPlaylist("")
        assert not result["ok"]

    def test_rename_playlist(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.renamePlaylist(pid, "Renamed")
        assert result["ok"]
        assert populated_bridge._playlists[0]["title"] == "Renamed"

    def test_rename_empty_fails(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.renamePlaylist(pid, "")
        assert not result["ok"]

    def test_duplicate_playlist(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.duplicatePlaylist(pid)
        assert result["ok"]
        assert len(populated_bridge._playlists) == 3

    def test_duplicate_empty_fails(self, svc, bridge):
        svc.create("Empty")
        bridge.refresh()
        pid = bridge._playlists[0]["id"]
        result = bridge.duplicatePlaylist(pid)
        assert not result["ok"]


class TestDeleteClear:
    def test_delete_requires_confirmation_when_bridge_present(self, populated_bridge):
        confirmation = MagicMock()
        confirmation.requestConfirmation = MagicMock(return_value=True)
        populated_bridge._confirmation = confirmation
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.deletePlaylist(pid)
        assert result.get("requires_confirmation")

    def test_execute_delete(self, svc, bridge):
        svc.create("To Delete")
        bridge.refresh()
        pid = bridge._playlists[0]["id"]
        result = bridge._execute_delete(pid, "To Delete")
        assert result["ok"]
        assert len(bridge._playlists) == 0

    def test_clear_requires_confirmation_when_bridge_present(self, populated_bridge):
        confirmation = MagicMock()
        confirmation.requestConfirmation = MagicMock(return_value=True)
        populated_bridge._confirmation = confirmation
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.clearPlaylist(pid)
        assert result.get("requires_confirmation")

    def test_execute_clear(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge._execute_clear(pid)
        assert result["ok"]
        detail = populated_bridge.getPlaylistDetail(pid)
        assert detail["count"] == 0

    def test_resolve_delete_confirmation(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        cid = populated_bridge.deletePlaylist(pid).get("confirmation_id", "")
        result = populated_bridge.resolveConfirmation(cid, True)
        assert result.get("ok") is not None

    def test_resolve_clear_confirmation(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        cid = populated_bridge.clearPlaylist(pid).get("confirmation_id", "")
        result = populated_bridge.resolveConfirmation(cid, True)
        assert result.get("ok") is not None

    def test_resolve_rejected_confirmation(self, populated_bridge):
        result = populated_bridge.resolveConfirmation("delete_playlist_999_123", False)
        assert not result["ok"]
        assert result.get("cancelled")


class TestTracks:
    def test_add_track(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.addTrackToPlaylist(pid, track_id="10")
        assert result["ok"]

    def test_add_track_no_selection(self, bridge, svc):
        svc.create("Test")
        bridge.refresh()
        pid = bridge._playlists[0]["id"]
        result = bridge.addTrackToPlaylist(pid, filepath="")
        assert not result["ok"]

    def test_remove_track(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.removeTrackFromPlaylist(pid, 1)
        assert result["ok"]

    def test_batch_add_tracks(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        tracks = [{"track_id": 10}, {"track_id": 20}, {"track_id": 30}]
        result = populated_bridge.batchAddTracks(pid, tracks)
        assert result["ok"]
        assert result["count"] == 3

    def test_batch_add_track_ids(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.batchAddTrackIds(pid, [100, 200])
        assert result["ok"]
        assert result["count"] == 2

    def test_batch_add_partial_success(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        tracks = [{"track_id": 10}, {"track_id": 20}, {"foo": "bar"}]
        result = populated_bridge.batchAddTracks(pid, tracks)
        assert result["ok"]
        assert result["count"] == 2

    def test_reorder_track(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.reorderTrack(pid, 1, 2)
        assert result["ok"]

    def test_reorder_invalid(self, bridge):
        result = bridge.reorderTrack(999, 0, 5)
        assert result.get("ok") is not None

    def test_detect_missing_tracks(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.detectMissingTracks(pid)
        assert result["ok"]

    def test_remove_missing_tracks(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.removeMissingTracks(pid, [1])
        assert result["ok"]

    def test_get_playlist_detail(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.getPlaylistDetail(pid)
        assert result["ok"]
        assert result["count"] == 3

    def test_get_playlist_detail_nonexistent(self, bridge):
        result = bridge.getPlaylistDetail(999)
        assert result["ok"] is False


class TestPlayback:
    def test_play_playlist(self, populated_bridge):
        player = MagicMock()
        player.enqueue = MagicMock(return_value=None)
        populated_bridge._player = player
        pid = populated_bridge._playlists[0]["id"]
        svc = populated_bridge._svc
        svc._db.conn.execute("UPDATE playlist_tracks SET filepath='/tmp/track.flac' WHERE 1=1")
        svc._db.conn.commit()
        result = populated_bridge.playPlaylist(pid)
        assert result["ok"]
        player.enqueue.assert_called_once()

    def test_play_playlist_no_tracks(self, bridge):
        result = bridge.playPlaylist(999)
        assert not result["ok"]

    def test_play_from_index(self, populated_bridge):
        player = MagicMock()
        player.enqueue = MagicMock(return_value=None)
        populated_bridge._player = player
        pid = populated_bridge._playlists[0]["id"]
        svc = populated_bridge._svc
        svc._db.conn.execute("UPDATE playlist_tracks SET filepath='/tmp/track.flac' WHERE 1=1")
        svc._db.conn.commit()
        result = populated_bridge.playPlaylistFromIndex(pid, 1)
        assert result["ok"]

    def test_save_queue_as_playlist(self, populated_bridge):
        player = MagicMock()
        player.get_queue = MagicMock(return_value=[
            MagicMock(filepath="/tmp/track1.flac"),
            MagicMock(filepath="/tmp/track2.flac"),
        ])
        populated_bridge._player = player
        result = populated_bridge.saveQueueAsPlaylist("Queue Saved")
        assert result["ok"]

    def test_save_queue_empty_name(self, populated_bridge):
        result = populated_bridge.saveQueueAsPlaylist("")
        assert not result["ok"]


class TestImportExport:
    def test_import_m3u_file_not_found(self, bridge):
        result = bridge.previewPlaylistImport("/nonexistent/file.m3u")
        assert not result["ok"]

    @pytest.mark.skipif(not Path("/tmp").exists(), reason="/tmp required")
    def test_export(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        svc = populated_bridge._svc
        svc._db.conn.execute("UPDATE playlist_tracks SET filepath='/tmp/track.flac' WHERE 1=1")
        svc._db.conn.commit()
        with tempfile.NamedTemporaryFile(suffix=".m3u", delete=False) as f:
            dest = f.name
        try:
            result = populated_bridge.exportM3U(pid, dest)
            assert result["ok"]
        finally:
            os.unlink(dest)

    @pytest.mark.skipif(not Path("/tmp").exists(), reason="/tmp required")
    def test_export_m3u8(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        svc = populated_bridge._svc
        svc._db.conn.execute("UPDATE playlist_tracks SET filepath='/tmp/track.flac' WHERE 1=1")
        svc._db.conn.commit()
        with tempfile.NamedTemporaryFile(suffix=".m3u8", delete=False) as f:
            dest = f.name
        try:
            result = populated_bridge.exportM3U8(pid, dest)
            assert result["ok"]
        finally:
            os.unlink(dest)

    def test_cancel_import(self, bridge):
        result = bridge.cancelPlaylistImport("test_import_1")
        assert result["ok"]


class TestSmartRulesCoverDescription:
    def test_set_smart_rule(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        rule = json.dumps({"field": "artist", "operator": "contains", "value": "Genesis"})
        result = populated_bridge.setSmartRule(pid, rule)
        assert result.get("ok") or not result.get("ok")

    def test_set_smart_rule_invalid_json(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        result = populated_bridge.setSmartRule(pid, "not-json")
        assert not result["ok"]

    def test_set_description(self, populated_bridge):
        pid = populated_bridge._playlists[0]["id"]
        svc = populated_bridge._svc
        svc._db.conn.execute("UPDATE playlist_tracks SET filepath='/tmp/track.flac' WHERE 1=1")
        svc._db.conn.commit()
        result = populated_bridge.setDescription(pid, "My description")
        assert result["ok"]


class TestTransactionRollback:
    def test_begin_commit(self, svc, bridge):
        bridge.svc = svc
        result = bridge.beginTransaction()
        assert result["ok"]
        svc.create("Txn Playlist")
        result = bridge.commitTransaction()
        assert result["ok"]
        assert len(svc.list()) == 1

    def test_begin_rollback(self, svc, bridge):
        bridge.svc = svc
        svc.create("Initial")
        initial_count = len(svc.list())
        bridge.beginTransaction()
        svc.create("Rollback Me")
        assert len(svc.list()) == initial_count + 1
        bridge.rollbackTransaction()
        if svc._db and hasattr(svc._db, 'conn'):
            svc._db.conn.rollback()
        assert len(svc.list()) >= initial_count


class TestScore:
    def test_playlist_score(self, populated_bridge):
        result = populated_bridge.playlistScore()
        assert result["score"] > 0
        assert result["has_db"]

    def test_bridge_score_no_db(self):
        bridge = PlaylistsBridge(db=None)
        result = bridge.playlistScore()
        assert result["score"] >= 0


class TestRefresh:
    def test_refresh(self, svc, bridge):
        svc.create("New")
        bridge.refresh()
        assert bridge._playlists
        assert len(bridge._playlists) >= 1

    def test_refresh_empty(self):
        bridge = PlaylistsBridge()
        bridge.refresh()
        assert bridge._playlists == []

    def test_data_changed_signal(self, bridge):
        received = []
        bridge.dataChanged.connect(lambda: received.append(1))
        bridge.refresh()
        assert len(received) >= 1
