"""Tests for playlist audit service."""
from __future__ import annotations

import sqlite3
from library.playlists.playlist_audit import audit_playlist, audit_all_playlists, find_empty_playlists
from library.playlists.playlist_store import PlaylistStore


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    return PlaylistStore(conn)


class TestPlaylistAudit:
    def test_audit_empty(self):
        store = _make_store()
        pid = store.create_playlist("Empty")
        report = audit_playlist(store, pid)
        assert report.score == 0

    def test_audit_healthy(self):
        store = _make_store()
        pid = store.create_playlist("H")
        store.add_track(pid, filepath="/tmp/_michi_test.flac")
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
        pid = store.create_playlist("Empty")
        assert pid in find_empty_playlists(store)
