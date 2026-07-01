"""Tests for playlist audit service."""
from __future__ import annotations

import sqlite3
from library.playlists.playlist_audit import audit_playlist, audit_all_playlists, find_empty_playlists
from library.playlists.playlist_store import PlaylistStore


def _make_store() -> PlaylistStore:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    return PlaylistStore(conn)


class TestPlaylistAudit:

    def test_audit_empty_playlist(self):
        store = _make_store()
        pid = store.create_playlist("Empty")
        report = audit_playlist(store, pid)
        assert report.score == 0
        assert any(i.issue_type == "empty" for i in report.issues)

    def test_audit_healthy_playlist(self):
        store = _make_store()
        pid = store.create_playlist("Healthy")
        store.add_track(pid, filepath="/tmp/.michi_test_audit.flac")
        report = audit_playlist(store, pid)
        assert report.track_count >= 1

    def test_audit_all(self):
        store = _make_store()
        store.create_playlist("A")
        store.create_playlist("B")
        reports = audit_all_playlists(store)
        assert len(reports) >= 2

    def test_find_empty(self):
        store = _make_store()
        pid = store.create_playlist("Will Be Empty")
        empty = find_empty_playlists(store)
        assert pid in empty

    def test_audit_lost_file(self):
        store = _make_store()
        pid = store.create_playlist("Lost")
        store.add_track(pid, filepath="/definitely/does/not/exist/music.flac")
        report = audit_playlist(store, pid)
        lost_issues = [i for i in report.issues if i.issue_type == "lost"]
        assert len(lost_issues) >= 1
