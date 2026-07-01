"""Tests for PlaylistStore CRUD operations."""
from __future__ import annotations

import sqlite3

from library.playlists.playlist_store import PlaylistStore


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    return PlaylistStore(conn), conn


class TestPlaylistStore:
    def test_create_playlist(self):
        store, _ = _make_store()
        pid = store.create_playlist("Test")
        assert pid > 0
        assert store.get_playlist(pid)["name"] == "Test"

    def test_rename_playlist(self):
        store, _ = _make_store()
        pid = store.create_playlist("Old")
        store.rename_playlist(pid, "New")
        assert store.get_playlist(pid)["name"] == "New"

    def test_delete_playlist(self):
        store, _ = _make_store()
        pid = store.create_playlist("Del")
        store.delete_playlist(pid)
        assert store.get_playlist(pid) is None

    def test_duplicate_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("Orig")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?,?,?,?,?)",
                     ("/m/s.flac", "s.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/s.flac")
        nid = store.duplicate_playlist(pid)
        assert nid != pid
        assert store.get_playlist(nid)["name"] == "Orig (copia)"

    def test_add_track(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?,?,?,?,?)",
                     ("/m/s.flac", "s.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/s.flac")
        assert len(store.get_playlist_items(pid)) == 1

    def test_remove_track(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?,?,?,?,?)",
                     ("/m/s.flac", "s.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/s.flac")
        store.remove_track(pid, filepath="/m/s.flac")
        assert len(store.get_playlist_items(pid)) == 0

    def test_clear_playlist(self):
        store, _ = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/a.flac")
        store.add_track(pid, filepath="/b.flac")
        store.clear_playlist(pid)
        assert len(store.get_playlist_items(pid)) == 0

    def test_set_order_by_filepaths(self):
        store, _ = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/b.flac")
        store.add_track(pid, filepath="/a.flac")
        store.set_playlist_order(pid, ordered_filepaths=["/a.flac", "/b.flac"])
        assert store.get_playlist_items(pid)[0].filepath == "/a.flac"

    def test_move_item(self):
        store, _ = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/a.flac")
        store.add_track(pid, filepath="/b.flac")
        store.add_track(pid, filepath="/c.flac")
        store.move_item(pid, 0, 2)
        assert store.get_playlist_items(pid)[2].filepath == "/a.flac"
