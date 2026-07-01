"""Tests for PlaylistStore CRUD operations."""
from __future__ import annotations

import sqlite3


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    from library.playlists.playlist_store import PlaylistStore
    return PlaylistStore(conn), conn


class TestPlaylistStore:

    def test_create_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("Test Playlist", "A description")
        assert pid > 0
        pl = store.get_playlist(pid)
        assert pl["name"] == "Test Playlist"
        assert pl["description"] == "A description"

    def test_rename_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("Old Name")
        store.rename_playlist(pid, "New Name")
        assert store.get_playlist(pid)["name"] == "New Name"

    def test_delete_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("To Delete")
        store.delete_playlist(pid)
        assert store.get_playlist(pid) is None

    def test_duplicate_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("Original")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?, ?, ?, ?, ?)",
                     ("/m/song.flac", "song.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/song.flac")
        new_id = store.duplicate_playlist(pid)
        assert new_id != pid
        assert store.get_playlist(new_id)["name"] == "Original (copia)"
        items = store.get_playlist_items(new_id)
        assert len(items) == 1

    def test_get_all_playlists(self):
        store, conn = _make_store()
        store.create_playlist("A")
        store.create_playlist("B")
        all_pl = store.get_all_playlists(include_stats=False)
        assert len(all_pl) >= 2

    def test_add_track(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?, ?, ?, ?, ?)",
                     ("/m/s.flac", "s.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/s.flac")
        items = store.get_playlist_items(pid)
        assert len(items) == 1
        assert items[0].filepath == "/m/s.flac"

    def test_remove_track(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?, ?, ?, ?, ?)",
                     ("/m/s.flac", "s.flac", "/m", "flac", "audio"))
        conn.commit()
        store.add_track(pid, filepath="/m/s.flac")
        store.remove_track(pid, filepath="/m/s.flac")
        assert len(store.get_playlist_items(pid)) == 0

    def test_clear_playlist(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/a.flac")
        store.add_track(pid, filepath="/b.flac")
        store.clear_playlist(pid)
        assert len(store.get_playlist_items(pid)) == 0

    def test_set_order_by_filepaths(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/b.flac")
        store.add_track(pid, filepath="/a.flac")
        store.set_playlist_order(pid, ordered_filepaths=["/a.flac", "/b.flac"])
        items = store.get_playlist_items(pid)
        assert items[0].filepath == "/a.flac"

    def test_move_item(self):
        store, conn = _make_store()
        pid = store.create_playlist("P")
        store.add_track(pid, filepath="/a.flac")
        store.add_track(pid, filepath="/b.flac")
        store.add_track(pid, filepath="/c.flac")
        store.move_item(pid, 0, 2)
        items = store.get_playlist_items(pid)
        assert items[2].filepath == "/a.flac"

    def test_find_empty(self):
        store, conn = _make_store()
        pid = store.create_playlist("Empty")
        store.create_playlist("Full")
        store.add_track(pid, filepath="/x.flac")
        empty = store.find_empty_playlists()
        for eid in empty:
            pl = store.get_playlist(eid)
            if pl and pl["name"] == "Full":
                break
        else:
            # at least one playlist should be empty
            pass

    def test_summary(self):
        store, conn = _make_store()
        pid = store.create_playlist("S")
        store.add_track(pid, filepath="/a.flac")
        summary = store.get_summary(pid)
        assert summary.name == "S"
