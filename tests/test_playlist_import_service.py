"""Tests for playlist import service."""
from __future__ import annotations

import json
import os
import tempfile

from library.playlists.playlist_import import preview_import, import_as_playlist, _parse_playlist_file


def _make_m3u(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _make_store():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    from library.playlists.playlist_store import PlaylistStore
    return PlaylistStore(conn)


class TestPlaylistImport:

    def test_parse_m3u_absolute(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("#EXTM3U\n#EXTINF:120,Artist - Song\n/music/song.flac\n")
            path = f.name
        entries = _parse_playlist_file(path)
        assert len(entries) == 1
        assert entries[0]["filepath"] == "/music/song.flac"
        os.unlink(path)

    def test_parse_m3u8(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u8", mode="w", delete=False, encoding="utf-8") as f:
            f.write("#EXTM3U\n#PLAYLIST:Test\n/m/s.flac\n")
            path = f.name
        entries = _parse_playlist_file(path)
        assert len(entries) == 1
        os.unlink(path)

    def test_parse_pls(self):
        with tempfile.NamedTemporaryFile(suffix=".pls", mode="w", delete=False, encoding="utf-8") as f:
            f.write("[playlist]\nFile1=/m/song.flac\nFile2=/m/song2.flac\n")
            path = f.name
        entries = _parse_playlist_file(path)
        assert len(entries) == 2
        os.unlink(path)

    def test_preview_found_missing(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write("/nonexistent/file.flac\n")
            path = f.name
        preview = preview_import(path)
        assert preview.total_entries == 1
        assert preview.missing == 1
        os.unlink(path)

    def test_preview_found_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".m3u", mode="w", delete=False, encoding="utf-8") as f:
            f.write(f"{f.name}\n")
            path = f.name
        preview = preview_import(path)
        assert preview.total_entries == 1
        assert preview.found >= 0
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
            f.write("/tmp/test_exists.flac\n")
            path = f.name
        result = import_as_playlist(path, store)
        assert result.ok
        assert result.playlist_id > 0
        os.unlink(path)

    def test_import_michi_json(self):
        store = _make_store()
        data = {
            "format": "michi.playlist.v1",
            "playlist": {"name": "JSON Import"},
            "tracks": [{"filepath": "/tmp/jt.flac", "title": "Test"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(data, f)
            path = f.name
        result = import_as_playlist(path, store)
        assert result.ok
        os.unlink(path)

    def test_preview_invalid_file(self):
        preview = preview_import("/nonexistent/file.m3u")
        assert preview.total_entries == 0
