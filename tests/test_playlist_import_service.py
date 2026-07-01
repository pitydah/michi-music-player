"""Tests for playlist import service."""
from __future__ import annotations

import json
import os
import tempfile
import sqlite3

from library.playlists.playlist_import import preview_import, import_as_playlist, _parse_playlist_file
from library.playlists.playlist_store import PlaylistStore


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    return PlaylistStore(conn)


class TestPlaylistImport:
    def test_parse_m3u_absolute(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("#EXTM3U\n#EXTINF:120,A - S\n/m/s.flac\n")
            path = f.name
        entries = _parse_playlist_file(path)
        assert len(entries) == 1
        os.unlink(path)

    def test_parse_pls(self):
        with tempfile.NamedTemporaryFile(suffix=".pls", mode="w", delete=False, encoding="utf-8") as f:
            f.write("[playlist]\nFile1=/m/s.flac\nFile2=/m/s2.flac\n")
            path = f.name
        entries = _parse_playlist_file(path)
        assert len(entries) == 2
        os.unlink(path)

    def test_preview_found_missing(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("/nonexistent/file.flac\n")
            path = f.name
        preview = preview_import(path)
        assert preview.missing == 1
        os.unlink(path)

    def test_preview_remote(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("https://example.com/stream\n")
            path = f.name
        preview = preview_import(path)
        assert preview.remote == 1
        os.unlink(path)

    def test_import_m3u_to_store(self):
        store = _make_store()
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("/tmp/test_ex.flac\n")
            path = f.name
        result = import_as_playlist(path, store)
        assert result.ok
        os.unlink(path)

    def test_import_michi_json(self):
        store = _make_store()
        data = {"format": "michi.playlist.v1", "playlist": {"name": "JSON"},
                "tracks": [{"filepath": "/tmp/jt.flac", "title": "T"}]}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            path = f.name
        result = import_as_playlist(path, store)
        assert result.ok
        os.unlink(path)
