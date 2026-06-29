"""Tests for sync_protocol — DTOs, serialization, token generation, helpers."""

import json


class TestDeviceInfo:
    def test_defaults(self):
        from sync.sync_protocol import DeviceInfo
        d = DeviceInfo(alias="test")
        assert d.alias == "test"
        assert d.device == "desktop"
        assert d.version == "1.0"

    def test_to_json(self):
        from sync.sync_protocol import DeviceInfo
        d = DeviceInfo(alias="test", device="android")
        j = d.to_json()
        parsed = json.loads(j)
        assert parsed["alias"] == "test"
        assert parsed["device"] == "android"

    def test_from_json(self):
        from sync.sync_protocol import DeviceInfo
        j = '{"alias": "phone", "device": "android", "port": 53318}'
        d = DeviceInfo.from_json(j)
        assert d.alias == "phone"
        assert d.device == "android"
        assert d.port == 53318

    def test_from_json_ignores_extra(self):
        from sync.sync_protocol import DeviceInfo
        j = '{"alias": "x", "extra_field": "ignored"}'
        d = DeviceInfo.from_json(j)
        assert d.alias == "x"
        assert not hasattr(d, "extra_field")


class TestSessionToken:
    def test_defaults(self):
        from sync.sync_protocol import SessionToken
        t = SessionToken(token="abc")
        assert t.token == "abc"
        assert t.created > 0

    def test_generate(self):
        from sync.sync_protocol import SessionToken
        t = SessionToken.generate(device_alias="phone")
        assert len(t.token) == 64
        assert t.device_alias == "phone"

    def test_generates_unique(self):
        from sync.sync_protocol import SessionToken
        t1 = SessionToken.generate()
        t2 = SessionToken.generate()
        assert t1.token != t2.token

    def test_is_expired(self):
        from sync.sync_protocol import SessionToken
        t = SessionToken(token="abc", created=0)
        assert t.is_expired(max_age=1) is True

    def test_not_expired(self):
        from sync.sync_protocol import SessionToken
        import time
        t = SessionToken(token="abc", created=time.time())
        assert t.is_expired(max_age=3600) is False


class TestTrackDto:
    def test_defaults(self):
        from sync.sync_protocol import TrackDto
        t = TrackDto(id="abc123", title="Song")
        assert t.id == "abc123"
        assert t.title == "Song"
        assert t.duration == 0

    def test_to_dict_strips_filepath(self):
        from sync.sync_protocol import TrackDto
        t = TrackDto(id="abc", title="Song", filepath="/secret/music.mp3")
        d = t.to_dict()
        assert "filepath" not in d
        assert d["title"] == "Song"


class TestLibraryResponse:
    def test_to_json(self):
        from sync.sync_protocol import LibraryResponse
        resp = LibraryResponse(tracks=[{"id": "1"}], total=1)
        j = json.loads(resp.to_json())
        assert j["total"] == 1
        assert len(j["tracks"]) == 1


class TestRegisterRequest:
    def test_from_json(self):
        from sync.sync_protocol import RegisterRequest
        j = '{"alias": "phone", "device": "android", "device_model": "Pixel"}'
        req = RegisterRequest.from_json(j)
        assert req.alias == "phone"
        assert req.device == "android"
        assert req.device_model == "Pixel"

    def test_from_json_ignores_extra(self):
        from sync.sync_protocol import RegisterRequest
        j = '{"alias": "x", "unknown": "ignored"}'
        req = RegisterRequest.from_json(j)
        assert req.alias == "x"


class TestSyncStateRequest:
    def test_from_json(self):
        from sync.sync_protocol import SyncStateRequest
        j = '{"session_token": "tok123", "tracks": [{"track_id": "1"}]}'
        req = SyncStateRequest.from_json(j)
        assert req.session_token == "tok123"
        assert len(req.tracks) == 1


class TestRegisterResponse:
    def test_to_json(self):
        from sync.sync_protocol import RegisterResponse
        resp = RegisterResponse(
            session_token="tok", server_device_id="srv",
            client_device_id="cli", library_size=100)
        j = json.loads(resp.to_json())
        assert j["session_token"] == "tok"
        assert j["library_size"] == 100


class TestConstants:
    def test_multicast_group(self):
        from sync.sync_protocol import MULTICAST_GROUP
        assert MULTICAST_GROUP == "224.0.0.167"

    def test_ports(self):
        from sync.sync_protocol import MULTICAST_PORT, SYNC_PORT
        assert MULTICAST_PORT == 53318
        assert SYNC_PORT == 53318


class TestAnnounceMessage:
    def test_defaults(self):
        from sync.sync_protocol import AnnounceMessage
        msg = AnnounceMessage(alias="server")
        assert msg.type == "announce"
        assert msg.device == "desktop"

    def test_to_json(self):
        from sync.sync_protocol import AnnounceMessage
        msg = AnnounceMessage(alias="srv", type="goodbye")
        j = json.loads(msg.to_json())
        assert j["type"] == "goodbye"
        assert j["alias"] == "srv"

    def test_from_json(self):
        from sync.sync_protocol import AnnounceMessage
        j = '{"type": "announce", "alias": "phone", "device": "android"}'
        msg = AnnounceMessage.from_json(j)
        assert msg.alias == "phone"

    def test_from_json_ignores_extra(self):
        from sync.sync_protocol import AnnounceMessage
        j = '{"alias": "x", "extra": "ignored"}'
        msg = AnnounceMessage.from_json(j)
        assert msg.alias == "x"


class TestMakeTrackId:
    def test_mb_prefix(self):
        from sync.sync_protocol import make_track_id
        tid = make_track_id("/music/song.mp3", "mb:uuid-1234")
        assert tid == "uuid-1234"

    def test_fp_prefix(self):
        from sync.sync_protocol import make_track_id
        tid = make_track_id("/music/song.mp3", "fp:abc123def456")
        assert tid == "abc123def456"

    def test_fallback(self):
        from sync.sync_protocol import make_track_id
        tid = make_track_id("/music/song.mp3")
        assert len(tid) == 16

    def test_consistent(self):
        from sync.sync_protocol import make_track_id
        t1 = make_track_id("/music/song.mp3")
        t2 = make_track_id("/music/song.mp3")
        assert t1 == t2

    def test_different_paths(self):
        from sync.sync_protocol import make_track_id
        t1 = make_track_id("/music/a.mp3")
        t2 = make_track_id("/music/b.mp3")
        assert t1 != t2


class TestPairStartResponse:
    def test_contract(self):
        from sync.sync_protocol import PairStartResponse
        resp = PairStartResponse(
            pairing_id="abc123",
            auth_methods=["password"],
            server_alias="Michi Music Player",
            auth_required=True,
            server_device_id="srv001",
        )
        j = json.loads(resp.to_json())
        assert j["pairing_id"] == "abc123"
        assert j["auth_methods"] == ["password"]
        assert j["server_alias"] == "Michi Music Player"
        assert j["auth_required"] is True
        assert j["server_device_id"] == "srv001"
        assert j["version"] == "1.0"


class TestPairConfirmRequest:
    def test_from_json_with_alias(self):
        from sync.sync_protocol import PairConfirmRequest
        j = '{"client_device_id": "android_123", "alias": "My Phone", "device_model": "Pixel", "port": 53318, "username": "user", "password": "pass"}'
        req = PairConfirmRequest.from_json(j)
        assert req.client_device_id == "android_123"
        assert req.alias == "My Phone"
        assert req.device_model == "Pixel"
        assert req.port == 53318

    def test_from_json_minimal(self):
        from sync.sync_protocol import PairConfirmRequest
        j = '{"client_device_id": "android_123", "username": "u", "password": "p"}'
        req = PairConfirmRequest.from_json(j)
        assert req.client_device_id == "android_123"
        assert req.alias == ""
        assert req.device_model == ""


class TestPairConfirmResponse:
    def test_contract(self):
        from sync.sync_protocol import PairConfirmResponse
        resp = PairConfirmResponse(
            success=True,
            device_id="android_123",
            device_token="tok_abc",
            permissions=["sync.read_manifest", "sync.download_tracks"],
            server_device_id="srv001",
            server_alias="Michi Music Player",
        )
        j = json.loads(resp.to_json())
        assert j["success"] is True
        assert j["device_id"] == "android_123"
        assert j["device_token"] == "tok_abc"
        assert j["permissions"] == ["sync.read_manifest", "sync.download_tracks"]
        assert j["server_device_id"] == "srv001"
        assert j["server_alias"] == "Michi Music Player"
        assert j["session_token"] == ""

    def test_error_response(self):
        from sync.sync_protocol import PairConfirmResponse
        resp = PairConfirmResponse(success=False, error="Invalid credentials")
        j = json.loads(resp.to_json())
        assert j["success"] is False
        assert j["error"] == "Invalid credentials"


class TestMakeDeviceId:
    def test_returns_string(self):
        from sync.sync_protocol import make_device_id
        did = make_device_id()
        assert isinstance(did, str)
        assert len(did) > 0
