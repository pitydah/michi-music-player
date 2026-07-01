"""Tests for playlist export service."""
from __future__ import annotations

import json
import os
import tempfile
import sqlite3

from library.playlists.playlist_export import export_m3u, export_txt, export_csv, export_michi_json
from library.playlists.playlist_store import PlaylistStore


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    store = PlaylistStore(conn)
    pid = store.create_playlist("Export Test")
    store.add_track(pid, filepath="/m/song.flac")
    store.add_track(pid, filepath="/m/song2.flac")
    return store, pid


class TestPlaylistExport:
    def test_export_m3u(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".m3u", delete=False, mode="w") as f:
            path = f.name
        result = export_m3u(store, pid, path)
        assert result["ok"]
        with open(path) as f:
            assert "#EXTM3U" in f.read()
        os.unlink(path)

    def test_export_txt(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            path = f.name
        result = export_txt(store, pid, path)
        assert result["ok"]
        os.unlink(path)

    def test_export_csv(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        result = export_csv(store, pid, path)
        assert result["ok"]
        os.unlink(path)

    def test_export_michi_json(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        result = export_michi_json(store, pid, path)
        assert result["ok"]
        with open(path) as f:
            data = json.load(f)
        assert data["format"] == "michi.playlist.v1"
        os.unlink(path)
