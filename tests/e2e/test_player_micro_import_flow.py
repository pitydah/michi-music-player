"""E2E: Player → Micro Server import flow — full lifecycle with mocks.

Tests: discover → pair → create session → upload tracks (with hash verify) →
upload artwork → upload playlist → commit → rollback.
Also tests continue_on_server, remote library, and diagnostics.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from integrations.michi_link.client import RemoteServerInfo


def _make_server() -> RemoteServerInfo:
    return RemoteServerInfo(
        host="10.0.0.100",
        port=53318,
        alias="MicroTest",
        server_device_id="micro_001",
        requires_pairing=True,
        device_token="tok_abc123",
        device_id="player_d1",
    )


class TestMicroServerService:
    def test_discover(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        with patch.object(svc._client, "discover", return_value=_make_server()):
            result = svc.discover("10.0.0.100")
            assert result.ok
            assert result.data.alias == "MicroTest"

    def test_discover_fails(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        with patch.object(svc._client, "discover", return_value=None):
            result = svc.discover("10.0.0.200")
            assert not result.ok
            assert result.code == "DISCOVERY_FAILED"

    def test_discover_servers(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        with patch.object(svc._client, "discover", return_value=_make_server()):
            result = svc.discover_servers([("10.0.0.1", 53318)])
            assert result.ok
            assert len(result.data) == 1

    def test_pair_success(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        server = _make_server()
        with patch.object(svc._client, "pair", return_value=True):
            result = svc.pair(server, username="admin", password="pass")
            assert result.ok
            assert "device_token" in str(result.data)

    def test_pair_rejected(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        with patch.object(svc._client, "pair", return_value=False):
            result = svc.pair(_make_server())
            assert not result.ok
            assert result.code == "PAIR_FAILED"

    def test_test_connection_success(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.test_connection(_make_server())
            assert result.ok

    def test_get_capabilities(self):
        from integrations.michi_link.services.micro_server_service import (
            MicroServerService,
        )
        svc = MicroServerService()
        result = svc.get_capabilities(_make_server())
        assert result.ok
        assert result.data["alias"] == "MicroTest"


class TestImportToServerService:
    def test_create_session(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        result = svc.create_session(_make_server(), ["t1", "t2", "t3"])
        assert result.ok
        assert result.data["total_tracks"] == 3
        assert result.data["session_id"] != ""

    def test_upload_track(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"fake_audio_data"
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            r2 = svc.upload_track(sid, "t1", "/api/v1/stream/t1")
            assert r2.ok
            assert r2.data["bytes"] > 0

    def test_upload_track_with_local_hash(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"test_audio")
            local = f.name
        try:
            svc = ImportToServerService()
            r1 = svc.create_session(_make_server(), ["t1"])
            sid = r1.data["session_id"]
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b"test_audio"
                mock_urlopen.return_value.__enter__.return_value = mock_resp
                r2 = svc.upload_track(sid, "t1", "/api/v1/stream/t1",
                                      local_filepath=local)
                assert r2.ok
                assert "local_hash" in r2.data
        finally:
            os.unlink(local)

    def test_upload_track_session_not_found(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        result = svc.upload_track("invalid", "t1", "/stream/t1")
        assert not result.ok
        assert result.code == "INVALID_SESSION"

    def test_upload_artwork(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake_art")
            art_path = f.name
        try:
            svc = ImportToServerService()
            r1 = svc.create_session(_make_server(), ["t1"])
            sid = r1.data["session_id"]
            result = svc.upload_artwork(sid, "cover_abc", artwork_path=art_path)
            assert result.ok
        finally:
            os.unlink(art_path)

    def test_upload_playlist(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        playlist = {"playlist_id": "pl_1", "name": "Test", "track_ids": ["t1"]}
        result = svc.upload_playlist(sid, playlist)
        assert result.ok

    def test_commit_success(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"d"
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            svc.upload_track(sid, "t1", "/api/v1/stream/t1")
        r2 = svc.commit(sid)
        assert r2.ok
        assert r2.data["uploaded"] == 1

    def test_commit_with_errors(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        svc._sessions[sid].errors.append("test error")
        result = svc.commit(sid)
        assert not result.ok
        assert result.code == "HAS_ERRORS"

    def test_rollback(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        result = svc.rollback(sid)
        assert result.ok
        assert svc.get_session(sid) is None

    def test_status(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        result = svc.status(sid)
        assert result.ok
        assert result.data["total"] == 1


class TestContinueOnServer:
    def test_transfer_queue(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        svc = ContinueOnServerService()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = json.dumps({"ok": True})
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.transfer_queue(_make_server(), ["t1", "t2"], position_ms=30000)
            assert result.ok

    def test_transfer_queue_with_provider(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        provider_called = False

        def queue_provider():
            nonlocal provider_called
            provider_called = True
            return (["t1", "t2"], 0, 15000.0)

        pause_called = False

        def pause_local():
            nonlocal pause_called
            pause_called = True

        svc = ContinueOnServerService(queue_provider=queue_provider,
                                       pause_local=pause_local)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = json.dumps({"ok": True})
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.transfer_queue(_make_server())
            assert result.ok
            assert provider_called
            assert pause_called

    def test_transfer_queue_with_resolver(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )

        def resolve(t):
            return f"resolved_{t}"

        svc = ContinueOnServerService(resolve_track=resolve)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = json.dumps({"ok": True})
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.transfer_queue(_make_server(), ["t1", "t2"])
            assert result.ok

    def test_start_remote_playback(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        svc = ContinueOnServerService()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.start_remote_playback(_make_server())
            assert result.ok

    def test_stop_remote_playback(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        svc = ContinueOnServerService()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.stop_remote_playback(_make_server())
            assert result.ok


class TestRemoteLibrary:
    def test_browse_tracks(self):
        from integrations.michi_link.services.remote_library_service import (
            RemoteLibraryService,
        )
        svc = RemoteLibraryService()
        with patch.object(svc._micro, "get_tracks") as mock_gt:
            mock_gt.return_value = type("R", (), {"ok": True, "data": [{"id": 1}, {"id": 2}]})()
            result = svc.browse_tracks(_make_server(), offset=0, limit=1)
            assert result.ok
            assert len(result.data["tracks"]) == 1
            assert result.data["total"] == 2

    def test_browse_tracks_returns_all(self):
        from integrations.michi_link.services.remote_library_service import (
            RemoteLibraryService,
        )
        svc = RemoteLibraryService()
        with patch.object(svc._micro, "get_tracks") as mock_gt:
            mock_gt.return_value = type("R", (), {"ok": True, "data": [{"id": 1}]})()
            result = svc.browse_tracks(_make_server())
            assert result.ok
            assert len(result.data["tracks"]) == 1

    def test_get_track_count(self):
        from integrations.michi_link.services.remote_library_service import (
            RemoteLibraryService,
        )
        svc = RemoteLibraryService()
        with patch.object(svc._micro, "get_library_stats") as mock_stats:
            mock_stats.return_value = type("R", (), {"ok": True, "data": {"audio": 42}})()
            count = svc.get_track_count(_make_server())
            assert count == 42

    def test_get_track_count_zero_on_failure(self):
        from integrations.michi_link.services.remote_library_service import (
            RemoteLibraryService,
        )
        svc = RemoteLibraryService()
        with patch.object(svc._micro, "get_library_stats") as mock_stats:
            mock_stats.return_value = type("R", (), {"ok": False})()
            count = svc.get_track_count(_make_server())
            assert count == 0


class TestResult:
    def test_result_success(self):
        from integrations.michi_link.services.result import Result
        r = Result.success({"id": 1}, "ok")
        assert r.ok
        assert r.code == "OK"
        assert r.data["id"] == 1

    def test_result_fail(self):
        from integrations.michi_link.services.result import Result
        r = Result.fail("ERR", "fail msg")
        assert not r.ok
        assert r.code == "ERR"
        assert r.message == "fail msg"

    def test_result_to_dict(self):
        from integrations.michi_link.services.result import Result
        r = Result.success(42)
        d = r.to_dict()
        assert d["ok"] is True
        assert d["code"] == "OK"
        assert d["data"] == 42


class TestDiagnosticsService:
    def test_generates_report(self):
        from integrations.michi_link.services.diagnostics_service import (
            DiagnosticsService,
        )
        svc = DiagnosticsService()
        report = svc.generate_report(registry=MagicMock())
        assert "player_api" in report
        assert "sync_server" in report
        assert "pairing" in report
        assert "stream" in report
        assert "playback" in report
        assert "queue" in report
        assert "micro_server_client" in report
        assert "micro_import" in report
        assert "continue_readiness" in report
        assert "errors" in report

    def test_pairing_with_devices(self):
        from integrations.michi_link.services.diagnostics_service import (
            DiagnosticsService,
        )
        svc = DiagnosticsService()
        registry = MagicMock()
        dev1 = MagicMock()
        dev1.token_hash = "abc"
        dev1.revoked_at = ""
        dev2 = MagicMock()
        dev2.token_hash = "def"
        dev2.revoked_at = "2025-01-01"
        registry.list_all.return_value = [dev1, dev2]
        result = svc.check_pairing(registry)
        assert result["status"] == "ok"
        assert result["paired"] == 1
        assert result["revoked"] == 1

    def test_diagnostics_remote_micro(self):
        from integrations.michi_link.services.diagnostics_service import (
            DiagnosticsService,
        )
        svc = DiagnosticsService()
        result = svc.check_remote_micro("10.0.0.99")
        assert result["status"] in ("unreachable", "skipped")

    def test_continue_readiness_no_queue(self):
        from integrations.michi_link.services.diagnostics_service import (
            DiagnosticsService,
        )
        svc = DiagnosticsService()
        ps = MagicMock()
        ps.get_queue.return_value = []
        result = svc.check_continue_readiness(ps)
        assert result["status"] == "no_queue"
