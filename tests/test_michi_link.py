"""Tests for Michi Link API v1 — server info, pairing, permissions, playback, legacy."""
from __future__ import annotations

import json
from unittest.mock import MagicMock


class TestServerInfo:
    def test_contract(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        d = info.to_dict()
        assert d["service"] == "michi-music-player"
        assert d["api_version"] == "v1"
        assert "desktop_player" in d["roles"]
        assert "library_master" in d["roles"]
        assert "remote_control_target" in d["roles"]
        assert "cast_controller" in d["roles"]
        assert "library" in d["features"]
        assert d["features"]["remote_control"] is True
        assert d["features"]["queue"] is True
        assert d["features"]["token_refresh"] is False
        assert d["features"]["events"] is False

    def test_server_info_has_version_and_michi_link_version(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        d = info.to_dict()
        assert d.get("version") == "1.0.0"
        assert d.get("michi_link_version") == "1.0.0-alpha"

    def test_server_info_has_auth_block(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        d = info.to_dict()
        auth = d.get("auth", {})
        assert auth.get("strategy") == "PLAYER_PASSWORD"
        assert auth.get("token_refresh") is False
        assert "required" in auth

    def test_server_info_features_receivers_and_rooms_false(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        d = info.to_dict()
        assert d["features"].get("receivers") is False
        assert d["features"].get("rooms") is False
        assert d["features"].get("token_refresh") is False
        assert d["features"].get("events") is False

    def test_server_info_includes_roles_features(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        d = info.to_dict()
        assert len(d["roles"]) == 5
        assert len(d["features"]) >= 10


class TestPairStart:
    def test_v1_pair_start_response(self):
        from integrations.michi_link.models import V1PairStartResponse
        resp = V1PairStartResponse(
            pairing_id="abc",
            auth_methods=["password"],
            server_alias="Michi",
            auth_required=True,
            server_device_id="srv001",
        )
        j = json.loads(resp.to_json())
        assert j["pairing_id"] == "abc"
        assert j["auth_methods"] == ["password"]
        assert j["auth_required"] is True
        assert j["server_device_id"] == "srv001"


class TestPairConfirm:
    def test_v1_pair_confirm_response(self):
        from integrations.michi_link.models import V1PairConfirmResponse
        resp = V1PairConfirmResponse(
            success=True,
            device_id="android_123",
            device_token="tok_xyz",
            permissions=["library.read", "playback.control"],
            server_device_id="srv001",
        )
        j = json.loads(resp.to_json())
        assert j["success"] is True
        assert j["device_id"] == "android_123"
        assert j["device_token"] == "tok_xyz"
        assert "library.read" in j["permissions"]
        assert j["server_device_id"] == "srv001"

    def test_v1_pair_confirm_error(self):
        from integrations.michi_link.models import V1PairConfirmResponse
        resp = V1PairConfirmResponse(success=False, error="Invalid credentials")
        j = json.loads(resp.to_json())
        assert j["success"] is False
        assert j["error"] == "Invalid credentials"

    def test_v1_pair_confirm_request_from_json(self):
        from integrations.michi_link.models import V1PairConfirmRequest
        j = '{"client_device_id":"d1","username":"u","password":"p",' \
            '"alias":"Phone","device_model":"Pixel","port":53318,"client_version":"1.0"}'
        req = V1PairConfirmRequest.from_json(j)
        assert req.client_device_id == "d1"
        assert req.alias == "Phone"
        assert req.device_model == "Pixel"


class TestPermissions:
    def test_v1_permissions_defined(self):
        from integrations.michi_link.permissions import V1_PERMISSIONS
        assert "library.read" in V1_PERMISSIONS
        assert "stream.read" in V1_PERMISSIONS
        assert "playback.read" in V1_PERMISSIONS
        assert "playback.control" in V1_PERMISSIONS
        assert "queue.read" in V1_PERMISSIONS

    def test_endpoint_permission_map(self):
        from integrations.michi_link.permissions import V1_ENDPOINT_PERMISSIONS
        assert V1_ENDPOINT_PERMISSIONS["GET/api/v1/library/stats"] == "library.read"
        assert V1_ENDPOINT_PERMISSIONS["POST/api/v1/playback/control"] == "playback.control"


class TestPlaybackState:
    def test_playback_state_dto(self):
        from integrations.michi_link.models import PlaybackStateDto
        dto = PlaybackStateDto(
            state="playing",
            current_track={"track_id": "abc", "title": "Song"},
            position_ms=12345.0,
            duration_ms=300000.0,
            volume=80,
            shuffle=False,
            repeat="none",
        )
        d = dto.to_dict()
        assert d["state"] == "playing"
        assert d["position_ms"] == 12345.0
        assert d["volume"] == 80
        assert d["repeat"] == "none"

    def test_queue_dto(self):
        from integrations.michi_link.models import QueueDto
        dto = QueueDto(
            tracks=[{"track_id": "1", "title": "A"}],
            current_index=0,
        )
        d = dto.to_dict()
        assert len(d["tracks"]) == 1
        assert d["current_index"] == 0


class TestStreamAlias:
    def test_stream_requires_permission(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/stream/track_hash_123"
        handler._require_permission = MagicMock(return_value=False)

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        handler._require_permission.assert_called_with("stream.read")

    def test_stream_returns_404_for_missing_track(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/stream/unknown_hash"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._resolve_track = MagicMock(return_value=None)
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        assert len(results) == 1
        data, status = results[0]
        assert "error" in data
        assert data["error"]["code"] == "TRACK_NOT_FOUND"

    def test_stream_404_has_details(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/stream/missing_hash"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._resolve_track = MagicMock(return_value=None)
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        data = results[0][0]
        assert isinstance(data.get("error", {}).get("details", {}), dict)

    def test_stream_200_without_range(self):
        from integrations.michi_link.server import V1_MIXIN
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 1024)
            tmp_path = f.name

        try:
            handler = MagicMock()
            handler.path = "/api/v1/stream/test_hash"
            handler._require_permission = MagicMock(return_value=True)
            handler.headers = {}
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()

            srv = MagicMock()
            srv._resolve_track = MagicMock(return_value=tmp_path)
            handler.server_ref = srv

            V1_MIXIN.handle_get(handler)
            # 200 response
            status = handler.send_response.call_args[0][0]
            assert status in (200, None)
        finally:
            os.unlink(tmp_path)

    def test_stream_206_with_range(self):
        from integrations.michi_link.server import V1_MIXIN
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"x" * 65536)
            tmp_path = f.name

        try:
            handler = MagicMock()
            handler.path = "/api/v1/stream/test_hash"
            handler._require_permission = MagicMock(return_value=True)
            handler.headers = {"Range": "bytes=0-1023"}
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()

            srv = MagicMock()
            srv._resolve_track = MagicMock(return_value=tmp_path)
            handler.server_ref = srv

            V1_MIXIN.handle_get(handler)
            # Should get 206
            status = handler.send_response.call_args[0][0]
            assert status == 206
        finally:
            os.unlink(tmp_path)


class TestArtworkAlias:
    def test_artwork_requires_permission(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/artwork/cover_hash_abc"
        handler._require_permission = MagicMock(return_value=False)

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        handler._require_permission.assert_called_with("artwork.read")

    def test_artwork_returns_404_for_missing_cover(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/artwork/unknown_hash"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._db.conn.execute.return_value.fetchone.return_value = None
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        assert len(results) == 1
        data, status = results[0]
        assert "error" in data
        assert data["error"]["code"] == "ARTWORK_NOT_FOUND"

    def test_artwork_200_with_mime_and_cache(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/artwork/cover_known"
        handler._require_permission = MagicMock(return_value=True)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()

        srv = MagicMock()
        row = ("image/jpeg", b"fake_image_data")
        srv._db.conn.execute.return_value.fetchone.return_value = row
        handler.server_ref = srv

        V1_MIXIN.handle_get(handler)
        handler.send_header.assert_any_call("Content-Type", "image/jpeg")
        handler.send_header.assert_any_call("Cache-Control", "public, max-age=86400")
        handler.wfile.write.assert_called_with(b"fake_image_data")


class TestSearch:
    def test_search_does_not_expose_filepath(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/search?q=test"
        handler._require_permission = MagicMock(return_value=True)

        srv = MagicMock()
        item = MagicMock()
        item.filepath = "/secret/path/song.mp3"
        item.title = "Test"
        item.artist = "Artist"
        item.album = "Album"
        item.duration = 200.0
        item.track_uid = ""
        srv._db.search_advanced.return_value = [item]
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)

        assert len(results) == 1
        body = results[0][0]
        for r in body.get("results", []):
            assert "filepath" not in r
            assert r["download_path"].startswith("/api/v1/stream/")

    def test_search_returns_track_id_compatible_with_stream(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/search?q=test"
        handler._require_permission = MagicMock(return_value=True)

        srv = MagicMock()
        item = MagicMock()
        item.filepath = "/music/song.mp3"
        item.title = "Test"
        item.artist = "A"
        item.album = "B"
        item.duration = 200.0
        item.track_uid = ""
        srv._db.search_advanced.return_value = [item]
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)

        body = results[0][0]
        for r in body.get("results", []):
            assert r["download_path"] == f"/api/v1/stream/{r['track_id']}"


class TestPlaybackControl:
    def test_accepts_command(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "play"})
        V1_MIXIN._handle_control(handler, body)
        ps.play_or_resume.assert_called_once()

    def test_accepts_action_as_fallback(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"action": "pause"})
        V1_MIXIN._handle_control(handler, body)
        ps.pause.assert_called_once()

    def test_set_volume_0(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "set_volume", "volume": 0})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(0)

    def test_set_volume_70(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "set_volume", "volume": 70})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(70)

    def test_set_volume_100(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "set_volume", "volume": 100})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(100)

    def test_set_volume_validates_range(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "set_volume", "volume": 150})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(100)

        body2 = json.dumps({"command": "set_volume", "volume": -10})
        V1_MIXIN._handle_control(handler, body2)
        ps.set_volume.assert_called_with(0)

    def test_toggle_calls_toggle(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "toggle"})
        V1_MIXIN._handle_control(handler, body)
        ps.toggle.assert_called_once()

    def test_toggle_fallback_without_toggle_method(self):
        from integrations.michi_link.server import V1_MIXIN
        from audio.player import PlaybackState
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock(spec=[])
        ps.pause = MagicMock()
        ps.play_or_resume = MagicMock()
        ps.state = PlaybackState.PLAYING
        # Remove toggle to trigger fallback
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "toggle"})
        V1_MIXIN._handle_control(handler, body)
        ps.pause.assert_called_once()

        ps.state = PlaybackState.PAUSED
        V1_MIXIN._handle_control(handler, body)
        ps.play_or_resume.assert_called()

    def test_seek_accepts_position_ms(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "seek", "position_ms": 30000})
        V1_MIXIN._handle_control(handler, body)
        ps.seek.assert_called_once_with(30.0)

    def test_seek_accepts_seek_ms_as_fallback(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "seek", "seek_ms": 15000})
        V1_MIXIN._handle_control(handler, body)
        ps.seek.assert_called_once_with(15.0)

    def test_seek_accepts_value_as_last_fallback(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "seek", "value": 5000})
        V1_MIXIN._handle_control(handler, body)
        ps.seek.assert_called_once_with(5.0)

    def test_mute_sets_volume_zero(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "mute"})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(0)

    def test_unmute_sets_volume_default(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        body = json.dumps({"command": "unmute"})
        V1_MIXIN._handle_control(handler, body)
        ps.set_volume.assert_called_once_with(70)

    def test_unknown_command_returns_v1_error(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler._require_permission = MagicMock(return_value=True)
        ps = MagicMock()
        V1_MIXIN._player_service = ps

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))

        body = json.dumps({"command": "fly"})
        V1_MIXIN._handle_control(handler, body)
        assert len(results) == 1
        data, status = results[0]
        assert "error" in data
        assert data["error"]["code"] == "UNKNOWN_COMMAND"


class TestSyncDelta:
    def test_accepts_cursor(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/sync/manifest/delta?device_id=d1&cursor=12345.0"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._delta_provider = MagicMock(return_value={"manifest_id": "m1"})
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))

        qs = {"device_id": ["d1"], "cursor": ["12345.0"]}
        # Patch parse_qs
        import urllib.parse
        orig_parse = urllib.parse.parse_qs
        urllib.parse.parse_qs = lambda x: qs

        V1_MIXIN.handle_get(handler)

        urllib.parse.parse_qs = orig_parse
        srv._delta_provider.assert_called_once_with("d1", 12345.0)
        assert len(results) == 1

    def test_accepts_manifest_id_as_fallback(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/sync/manifest/delta?device_id=d1&manifest_id=m_abc"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._delta_provider = MagicMock(return_value={"manifest_id": "m1"})
        handler.server_ref = srv

        import urllib.parse
        orig_parse = urllib.parse.parse_qs
        urllib.parse.parse_qs = lambda x: {"device_id": ["d1"], "manifest_id": ["m_abc"]}

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)

        urllib.parse.parse_qs = orig_parse
        assert len(results) == 1


class TestTokenRefresh:
    def test_returns_v1_error_not_implemented(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        handler.path = "/api/v1/token/refresh"
        handler._read_body = lambda: ""

        V1_MIXIN.handle_post(handler)
        assert len(results) == 1
        data, status = results[0]
        assert "error" in data
        assert data["error"]["code"] == "NOT_IMPLEMENTED"


class TestEvents:
    def test_returns_v1_error_not_implemented(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/events"
        handler._require_permission = MagicMock(return_value=True)

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))

        V1_MIXIN.handle_get(handler)
        assert len(results) == 1
        data, status = results[0]
        assert "error" in data
        assert data["error"]["code"] == "NOT_IMPLEMENTED"

    def test_server_info_declares_events_false(self):
        from integrations.michi_link.models import ServerInfo
        info = ServerInfo()
        assert info.features.get("events") is False
        assert info.features.get("token_refresh") is False


class TestTracks:
    def test_v1_tracks_no_filepath(self):
        from integrations.michi_link.server import V1_MIXIN

        handler = MagicMock()
        handler.path = "/api/v1/tracks"
        handler._require_permission = MagicMock(return_value=True)

        srv = MagicMock()
        item = MagicMock()
        item.filepath = "/secret/music/song.flac"
        item.title = "Test Song"
        item.artist = "Test Artist"
        item.album = "Test Album"
        item.duration = 200.0
        item.ext = ".flac"
        item.track_number = 1
        item.year = 2024
        item.bitrate = 1411
        item.sample_rate = 44100
        item.channels = 2
        item.size = 1000000
        item.genre = "Rock"
        item.track_uid = ""
        srv._db.get_all.return_value = [item]
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))

        V1_MIXIN.handle_get(handler)

        assert len(results) == 1
        body, status = results[0]
        tracks = body.get("tracks", [])
        assert len(tracks) == 1
        track = tracks[0]
        assert "filepath" not in track
        assert "track_id" in track
        assert track["title"] == "Test Song"
        assert track["download_path"].startswith("/api/v1/stream/")


class TestQueue:
    def test_build_queue_no_filepath(self):
        from integrations.michi_link.server import V1_MIXIN
        ps = MagicMock()
        ps.get_queue.return_value = [
            {"filepath": "/secret/song.mp3", "title": "Song",
             "artist": "A", "album": "B", "track_uid": ""},
        ]
        V1_MIXIN._player_service = ps
        V1_MIXIN._playback = MagicMock()
        V1_MIXIN._playback.get_queue_index.return_value = 0

        result = V1_MIXIN._build_queue(MagicMock())
        for t in result.get("tracks", []):
            assert "filepath" not in t
            assert t.get("download_path", "").startswith("/api/v1/stream/")
        assert result.get("current_index") == 0


class TestSyncManifest:
    def test_build_manifest_no_filepath(self):
        from integrations.michi_link.server import V1_MIXIN
        handler = MagicMock()
        handler.path = "/api/v1/sync/manifest?device_id=d1"
        handler._require_permission = MagicMock(return_value=True)
        srv = MagicMock()
        srv._manifest_provider = MagicMock(return_value={
            "tracks": [{"track_id": "abc", "title": "Song"}],
            "playlists": [],
        })
        handler.server_ref = srv

        results = []
        handler._send_json = lambda data, status=200: results.append((data, status))
        V1_MIXIN.handle_get(handler)
        assert len(results) == 1
        body = results[0][0]
        for t in body.get("tracks", []):
            assert "filepath" not in t


class TestServerIntegration:
    def test_server_info_mounts(self):
        from sync.sync_server import SyncServer, SyncRequestHandler
        from integrations.michi_link.server import MichiLinkServer
        db = MagicMock()
        SyncServer(db)
        MichiLinkServer.mount(SyncRequestHandler)
        assert hasattr(SyncRequestHandler, "_v1_mixin")


class TestLegacyCompat:
    def test_legacy_pair_start_still_works(self):
        from sync.sync_server import SyncRequestHandler
        assert hasattr(SyncRequestHandler, "do_GET")
