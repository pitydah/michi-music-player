"""Tests for Michi Link Playlist API endpoints."""
from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from library.schema import Schema
    Schema.initialize(conn)
    Schema.run_migrations(conn)
    from library.playlists.playlist_store import PlaylistStore
    store = PlaylistStore(conn)
    store.create_playlist("API Test", "From API")
    store.create_playlist("Smart Rock", is_smart=True, rules_json='{"rules":[{"field":"genre","op":"equals","value":"Rock"}]}')
    return conn, store


def _make_handler(conn):
    """Build a mock handler to exercise V1_MIXIN playlist handlers."""
    handler = MagicMock()
    srv = MagicMock()
    srv._db = MagicMock()
    srv._db.conn = conn
    srv._db._conn = conn
    handler.server_ref = srv
    handler.path = ""
    handler._send_json = MagicMock()
    handler._require_permission = MagicMock(return_value=True)
    return handler, srv


class TestPlaylistApi:

    def test_get_playlists(self):
        conn, _store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_get_playlists(handler, srv)
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "playlists" in data
        names = [p["name"] for p in data["playlists"]]
        assert "API Test" in names
        assert "Smart Rock" in names

    def test_get_playlist_by_id(self):
        conn, _store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_get_playlist(handler, srv, "/api/v1/playlists/1")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert data["name"] == "API Test"
        assert data["id"] == 1

    def test_get_playlist_not_found(self):
        conn, _store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_get_playlist(handler, srv, "/api/v1/playlists/999")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "error" in data

    def test_get_playlist_tracks(self):
        conn, store = _make_db()
        store.add_track(1, filepath="/api/test.flac")
        handler, srv = _make_handler(conn)
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?, ?, ?, ?, ?)",
                     ("/api/test.flac", "test.flac", "/api", "flac", "audio"))
        conn.commit()
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_get_playlist_tracks(handler, srv, "/api/v1/playlists/1/tracks")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "tracks" in data
        assert data["total"] >= 1

    def test_create_playlist_via_api(self):
        conn, _store = _make_db()
        handler, srv = _make_handler(conn)
        body = json.dumps({"name": "Created via API", "description": "Test"})
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_create_playlist(handler, srv, body)
        args, _ = handler._send_json.call_args
        data = args[0]
        assert data["status"] == "ok"
        assert data["name"] == "Created via API"

    def test_create_playlist_missing_name(self):
        conn, _store = _make_db()
        handler, srv = _make_handler(conn)
        body = json.dumps({"description": "No name"})
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_create_playlist(handler, srv, body)
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "error" in data

    def test_add_tracks_via_api(self):
        conn, store = _make_db()
        store.add_track(1, filepath="/api/t.flac")
        handler, srv = _make_handler(conn)
        body = json.dumps({"track_ids": ["/api/t.flac"]})
        conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind) VALUES (?, ?, ?, ?, ?)",
                     ("/api/t.flac", "t.flac", "/api", "flac", "audio"))
        conn.commit()
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_add_playlist_tracks(handler, srv, body, "/api/v1/playlists/1/tracks")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert data["added"] >= 1

    def test_reorder_playlist(self):
        conn, store = _make_db()
        store.add_track(1, filepath="/a.flac")
        store.add_track(1, filepath="/b.flac")
        handler, srv = _make_handler(conn)
        body = json.dumps({"order": ["/b.flac", "/a.flac"]})
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_reorder_playlist(handler, srv, body, "/api/v1/playlists/1/reorder")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert data["status"] == "ok"

    def test_delete_playlist(self):
        conn, store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_delete_playlist(handler, srv, "/api/v1/playlists/1")
        args, _ = handler._send_json.call_args
        data = args[0]
        assert data["deleted"] == 1
        assert store.get_playlist(1) is None

    def test_playlist_manifest(self):
        conn, store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_playlist_manifest(handler, srv)
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "playlists" in data
        assert data["format"] == "michi.playlists.manifest.v1"

    def test_playlist_delta(self):
        conn, store = _make_db()
        handler, srv = _make_handler(conn)
        handler.path = "/api/v1/playlists/manifest/delta?since=0"
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_playlist_delta(handler, srv)
        args, _ = handler._send_json.call_args
        data = args[0]
        assert "changed" in data or "playlists" in data

    def test_no_filepath_leak_in_manifest(self):
        conn, store = _make_db()
        handler, srv = _make_handler(conn)
        from integrations.michi_link.server import V1_MIXIN
        V1_MIXIN._handle_playlist_manifest(handler, srv)
        args, _ = handler._send_json.call_args
        data = args[0]
        for pl in data.get("playlists", []):
            assert "filepath" not in pl

    def test_auth_required_for_playlist_endpoints(self):
        from integrations.michi_link.permissions import V1_ENDPOINT_PERMISSIONS
        assert "GET/api/v1/playlists" in V1_ENDPOINT_PERMISSIONS
        assert "POST/api/v1/playlists" in V1_ENDPOINT_PERMISSIONS
        assert "DELETE/api/v1/playlists" in V1_ENDPOINT_PERMISSIONS

    def test_permissions_declared(self):
        from integrations.michi_link.permissions import V1_PERMISSIONS
        assert "playlist.read" in V1_PERMISSIONS
        assert "playlist.write" in V1_PERMISSIONS
