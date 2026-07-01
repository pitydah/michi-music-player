"""Tests for playlist export service."""
from __future__ import annotations

import json
import os
import tempfile

from library.playlists.playlist_export import export_m3u, export_m3u8, export_txt, export_csv, export_michi_json
from library.playlists.playlist_models import PlaylistExportOptions


def _make_store():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    from library.playlists.playlist_store import PlaylistStore
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
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "#EXTM3U" in content
        assert "song.flac" in content
        os.unlink(path)

    def test_export_m3u8(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".m3u8", delete=False, mode="w") as f:
            path = f.name
        result = export_m3u8(store, pid, path)
        assert result["ok"]
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
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "position" in content
        os.unlink(path)

    def test_export_michi_json(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        result = export_michi_json(store, pid, path, include_filepaths=True)
        assert result["ok"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["format"] == "michi.playlist.v1"
        assert len(data["tracks"]) == 2
        os.unlink(path)

    def test_export_michi_json_safe_mobile(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        result = export_michi_json(store, pid, path, include_filepaths=False, safe_mobile=True)
        assert result["ok"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for t in data["tracks"]:
            assert "filepath" not in t
        os.unlink(path)

    def test_export_relative_paths(self):
        store, pid = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".m3u", delete=False, mode="w") as f:
            path = f.name
        opts = PlaylistExportOptions(relative_paths=True)
        result = export_m3u(store, pid, path, opts)
        assert result["ok"]
        os.unlink(path)
