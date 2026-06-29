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
