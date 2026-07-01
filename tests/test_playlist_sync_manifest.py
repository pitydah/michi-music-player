"""Tests for playlist sync manifest."""
from __future__ import annotations

import sqlite3

from library.playlists.playlist_sync_manifest import build_manifest, build_delta, serialize_manifest_safe


def _make_store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    from library.playlists.playlist_store import PlaylistStore
    return PlaylistStore(conn), conn


class TestPlaylistSyncManifest:

    def test_build_manifest(self):
        store, conn = _make_store()
        store.create_playlist("Test PL")
        manifest = build_manifest(store, conn, device_id="desktop")
        assert manifest.format == "michi.playlists.manifest.v1"
        assert len(manifest.playlists) >= 1
        assert manifest.playlists[0].name == "Test PL"

    def test_build_delta(self):
        store, conn = _make_store()
        store.create_playlist("Delta PL")
        delta = build_delta(store, conn, since=0, device_id="desktop")
        assert "changed" in delta
        assert len(delta["changed"]) >= 1

    def test_serialize_safe(self):
        store, conn = _make_store()
        store.create_playlist("Safe PL")
        manifest = build_manifest(store, conn)
        safe = serialize_manifest_safe(manifest)
        assert "playlists" in safe
        for pl in safe["playlists"]:
            assert "filepath" not in pl
            assert "id" in pl
