"""E2E: Mobile → Player flow — full lifecycle test with mock server.

Tests the entire contract: server/info → pair/start → pair/confirm →
tracks → search → stream → artwork → playback → queue → jump.
Each step validates no filepath exposure and v1 error format.
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock


class FakeAccount:
    def exists(self): return True
    def get_username(self): return "testuser"
    def verify(self, pw): return pw == "correct"


def _make_srv():
    srv = MagicMock()
    srv._local_account = FakeAccount()
    srv._device_registry = MagicMock()
    srv._device_registry.get.return_value = None
    srv._device_registry.register = MagicMock()
    srv._device_registry.set_token = MagicMock()
    srv._sessions_lock = MagicMock()
    srv._sessions = {}
    srv._resolve_track.return_value = None
    srv.is_running = True
    srv._alias = "TestPlayer"
    srv.client_connected = MagicMock()
    item = MagicMock()
    item.filepath = "/secret/path/song.flac"
    item.title = "E2E Song"
    item.artist = "E2E Artist"
    item.album = "E2E Album"
    item.duration = 250.0
    item.ext = ".flac"
    item.size = 5000000
    item.year = 2024
    item.genre = "Test"
    item.track_uid = ""
    srv._db.get_all.return_value = [item]
    srv._db.search_advanced.return_value = [item]
    return srv, item


def _make_handler(path):
    handler = MagicMock()
    handler.path = path
    handler._require_permission = MagicMock(return_value=True)
    handler._check_rate_limit = MagicMock(return_value=True)
    handler._record_failed_attempt = MagicMock()
    handler.client_address = ("10.0.0.2", 54321)
    handler.headers = {}
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()
    return handler


class TestE2EMobilePlayerFlow:
    def _get_v1(self):
        from integrations.michi_link.server import V1_MIXIN
        return V1_MIXIN

    def _handle(self, handler, srv, method="GET"):
        v1 = self._get_v1()
        handler.server_ref = srv
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        if method == "GET":
            v1.handle_get(handler)
        else:
            v1.handle_post(handler)
        return results

    # ── server/info ──
    def test_server_info_returns_full_contract(self):
        srv, _ = _make_srv()
        results = self._handle(_make_handler("/api/v1/server/info"), srv)
        body = results[0][0]
        assert body["service"] == "michi-music-player"
        assert body["api_version"] == "v1"
        assert body["auth"]["strategy"] == "PLAYER_PASSWORD"
        assert body["features"]["events"] is False
        assert "filepath" not in str(body)

    # ── pair/start ──
    def test_pair_start_returns_auth_methods(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/pair/start")
        handler._read_body = lambda: '{"client_device_id":"mobile_1"}'
        results = self._handle(handler, srv, "POST")
        body = results[0][0]
        assert body["auth_methods"] == ["password"]
        assert body["auth_required"] is True
        assert body["pairing_id"] != ""

    # ── pair/confirm ──
    def test_pair_confirm_returns_token(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/pair/confirm")
        handler._read_body = lambda: json.dumps({
            "client_device_id": "mobile_abc",
            "username": "testuser",
            "password": "correct",
        })
        results = self._handle(handler, srv, "POST")
        body = results[0][0]
        assert body["success"] is True
        assert len(body["device_token"]) > 10
        assert "library.read" in body["permissions"]
        assert "playback.control" in body["permissions"]

    # ── tracks ──
    def test_tracks_no_filepath(self):
        srv, _ = _make_srv()
        results = self._handle(_make_handler("/api/v1/tracks"), srv)
        body = results[0][0]
        for t in body.get("tracks", []):
            assert "filepath" not in t
            assert t["download_path"].startswith("/api/v1/stream/")
            assert "track_id" in t
            assert "title" in t
            assert "artist" in t
            assert "album" in t

    # ── search ──
    def test_search_no_filepath(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/search?q=E2E")
        results = self._handle(handler, srv)
        body = results[0][0]
        for r in body.get("results", []):
            assert "filepath" not in r
            assert r["download_path"].startswith("/api/v1/stream/")

    # ── stream 200 ──
    def test_stream_200(self):
        srv, _ = _make_srv()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 2048)
            tmp = f.name
        try:
            srv._resolve_track.return_value = tmp
            handler = _make_handler("/api/v1/stream/hash123")
            handler.server_ref = srv
            v1 = self._get_v1()
            v1.handle_get(handler)
            status = handler.send_response.call_args[0][0]
            assert status in (200, None)
        finally:
            os.unlink(tmp)

    # ── stream 206 ──
    def test_stream_206_with_range(self):
        srv, _ = _make_srv()
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"x" * 65536)
            tmp = f.name
        try:
            srv._resolve_track.return_value = tmp
            handler = _make_handler("/api/v1/stream/hash456")
            handler.headers = {"Range": "bytes=0-1023"}
            handler.server_ref = srv
            v1 = self._get_v1()
            v1.handle_get(handler)
            status = handler.send_response.call_args[0][0]
            assert status == 206
        finally:
            os.unlink(tmp)

    # ── stream 404 ──
    def test_stream_404_has_details(self):
        srv, _ = _make_srv()
        srv._resolve_track.return_value = None
        handler = _make_handler("/api/v1/stream/missing")
        handler.server_ref = srv
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1 = self._get_v1()
        v1.handle_get(handler)
        body = results[0][0]
        assert body["error"]["code"] == "TRACK_NOT_FOUND"
        assert isinstance(body["error"]["details"], dict)

    # ── artwork ──
    def test_artwork_200_with_mime(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/artwork/cover_known")
        srv._db.conn.execute.return_value.fetchone.return_value = ("image/png", b"img")
        handler.server_ref = srv
        v1 = self._get_v1()
        v1.handle_get(handler)
        handler.send_header.assert_any_call("Content-Type", "image/png")
        handler.send_header.assert_any_call("Cache-Control", "public, max-age=86400")
        handler.wfile.write.assert_called_with(b"img")

    def test_artwork_404(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/artwork/unknown")
        srv._db.conn.execute.return_value.fetchone.return_value = None
        handler.server_ref = srv
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1 = self._get_v1()
        v1.handle_get(handler)
        assert results[0][0]["error"]["code"] == "ARTWORK_NOT_FOUND"

    # ── playback/state ──
    def test_playback_state(self):
        srv, _ = _make_srv()
        handler = _make_handler("/api/v1/playback/state")
        handler.server_ref = srv
        v1 = self._get_v1()
        v1._player_service = MagicMock()
        v1._player_service.state = MagicMock()
        v1._player_service.state.name = "STOPPED"
        v1._player_service.current = ""
        v1._playback = MagicMock()
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_get(handler)
        body = results[0][0]
        assert "state" in body
        assert "filepath" not in str(body)

    # ── playback/control ──
    def test_control_play(self):
        ps = MagicMock()
        v1 = self._get_v1()
        v1._player_service = ps
        handler = _make_handler("/api/v1/playback/control")
        handler._read_body = lambda: json.dumps({"command": "play"})
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_post(handler)
        ps.play_or_resume.assert_called_once()

    def test_control_pause(self):
        ps = MagicMock()
        v1 = self._get_v1()
        v1._player_service = ps
        handler = _make_handler("/api/v1/playback/control")
        handler._read_body = lambda: json.dumps({"command": "pause"})
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_post(handler)
        ps.pause.assert_called_once()

    def test_control_seek(self):
        ps = MagicMock()
        v1 = self._get_v1()
        v1._player_service = ps
        handler = _make_handler("/api/v1/playback/control")
        handler._read_body = lambda: json.dumps({"command": "seek", "position_ms": 60000})
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_post(handler)
        ps.seek.assert_called_once_with(60.0)

    def test_control_set_volume(self):
        ps = MagicMock()
        v1 = self._get_v1()
        v1._player_service = ps
        handler = _make_handler("/api/v1/playback/control")
        handler._read_body = lambda: json.dumps({"command": "set_volume", "volume": 75})
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_post(handler)
        ps.set_volume.assert_called_once_with(75)

    # ── queue ──
    def test_queue_no_filepath(self):
        v1 = self._get_v1()
        queue = MagicMock()
        queue.get_state.return_value = {
            "items": [{"filepath": "/secret/s.mp3", "title": "Q",
                       "artist": "A", "album": "B", "track_uid": ""}],
            "current_index": 0,
            "repeat": "none",
            "shuffle": False,
            "revision": 1,
        }
        v1._queue_service = queue
        result = v1._build_queue(MagicMock())
        for t in result.get("tracks", []):
            assert "filepath" not in t

    def test_queue_jump(self):
        v1 = self._get_v1()
        ps = MagicMock()
        queue = MagicMock()
        queue.play_from_index.return_value = {"ok": True}
        v1._player_service = ps
        v1._playback = ps
        v1._queue_service = queue
        handler = _make_handler("/api/v1/queue/jump")
        handler._read_body = lambda: json.dumps({"index": 1})
        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        v1.handle_post(handler)
        queue.play_from_index.assert_called_once_with(1)
        ps.play_queue.assert_not_called()
