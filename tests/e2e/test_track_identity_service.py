"""Tests for TrackIdentityService — hash, normalize, match, preflight payload."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch


class TestTrackIdentityHash:
    def test_compute_with_real_file(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"x" * 65536)
            path = f.name
        try:
            svc = TrackIdentityService()
            result = svc.compute(path, local_track_id="local_1")
            assert result.ok
            ident = result.data
            assert ident.local_track_id == "local_1"
            assert len(ident.sha256_prefix) == 32
            assert ident.file_size == 65536
        finally:
            os.unlink(path)

    def test_compute_with_db_item(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            path = f.name
        try:
            svc = TrackIdentityService()
            item = MagicMock()
            item.title = "Test Song"
            item.artist = "Test Artist"
            item.album = "Test Album"
            item.duration = 200.0
            result = svc.compute(path, db_item=item, local_track_id="t1")
            assert result.ok
            ident = result.data
            assert ident.title == "Test Song"
            assert ident.artist == "Test Artist"
            assert ident.duration_ms == 200000.0
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        svc = TrackIdentityService()
        result = svc.compute("/nonexistent/file.mp3")
        assert not result.ok
        assert result.code == "FILE_NOT_FOUND"

    def test_compute_from_dict(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"dict_test")
            path = f.name
        try:
            svc = TrackIdentityService()
            ident = svc.compute_from_dict({
                "filepath": path,
                "title": "Dict Song",
                "artist": "Dict Artist",
                "album": "Dict Album",
                "duration": 180.0,
                "size": 9,
            }, local_track_id="d1")
            assert ident.local_track_id == "d1"
            assert ident.title == "Dict Song"
            assert len(ident.sha256_prefix) == 32
        finally:
            os.unlink(path)

    def test_normalize(self):
        from integrations.michi_link.services.track_identity_service import (
            _normalize,
        )
        assert _normalize("  Hello   World  ") == "hello world"
        assert _normalize("  ") == ""
        assert _normalize("") == ""


class TestTrackIdentityMatch:
    def test_match_same_sha256(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        a = TrackIdentity(sha256_prefix="abc123", file_size=1000, duration_ms=200000)
        b = TrackIdentity(sha256_prefix="abc123", file_size=2000, duration_ms=300000)
        assert a.match(b)

    def test_match_normalized(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        a = TrackIdentity(
            sha256_prefix="", file_size=1000, duration_ms=200000,
            normalized_title="hello", normalized_artist="artist",
        )
        b = TrackIdentity(
            sha256_prefix="", file_size=1000, duration_ms=201000,
            normalized_title="hello", normalized_artist="artist",
        )
        assert a.match(b)

    def test_no_match_different_size(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        a = TrackIdentity(sha256_prefix="", file_size=1000, duration_ms=200000)
        b = TrackIdentity(sha256_prefix="", file_size=2000, duration_ms=200000)
        assert not a.match(b)

    def test_to_dict(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        ident = TrackIdentity(
            local_track_id="t1", sha256_prefix="abc",
            file_size=500, duration_ms=180000,
            title="S", artist="A", album="B",
        )
        d = ident.to_dict()
        assert d["local_track_id"] == "t1"
        assert d["sha256_prefix"] == "abc"
        assert d["file_size"] == 500

    def test_identity_to_preflight(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService, TrackIdentity,
        )
        svc = TrackIdentityService()
        ident = TrackIdentity(
            sha256_prefix="abc", file_size=500, duration_ms=180000,
            normalized_title="song", normalized_artist="artist",
            normalized_album="album",
        )
        payload = svc.identity_to_preflight(ident)
        assert payload["quick_hash"] == "abc"
        assert payload["file_size"] == 500
        assert payload["duration_ms"] == 180000
        assert "sha256_prefix" not in payload


class TestImportPreflight:
    def test_preflight_supported(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        with patch.object(svc, "_call_preflight", return_value={
            "results": [
                {"local_track_id": "t1", "exists": True,
                 "remote_track_id": "rt1"},
            ],
        }):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok
            assert result.data["t1"]["exists"] is True
            assert result.data["t1"]["remote_id"] == "rt1"

    def test_preflight_fallback_on_404(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 404
            from urllib.error import HTTPError
            mock_urlopen.side_effect = HTTPError(
                "http://10.0.0.1:53318/api/v1/import/preflight",
                404, "Not Found", {}, None,
            )

            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok
            assert result.data["t1"]["exists"] is False

    def test_preflight_fallback_on_connection_error(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen", side_effect=OSError("no route")):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok  # graceful fallback
            assert result.data["t1"]["exists"] is False


class TestImportMapping:
    def test_create_session_with_identities_and_mapping(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        ids = [TrackIdentity(local_track_id="t1")]

        with patch.object(svc, "_call_preflight", return_value={
            "results": [{"local_track_id": "t1", "exists": True,
                         "remote_track_id": "rt1"}],
        }):
            result = svc.create_session(server, ["t1"], identities=ids)
            assert result.ok
            assert result.data["existing"] == 1
            assert result.data["needs_upload"] == 0

    def test_create_session_without_identities(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        result = svc.create_session(server, ["t1", "t2"])
        assert result.ok
        assert result.data["total_tracks"] == 2
        assert result.data["needs_upload"] == 2


class TestContinueOnServer:
    def test_transfer_empty_queue_fails(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        svc = ContinueOnServerService(queue_provider=lambda: ([], 0, 0.0))
        from integrations.michi_link.client import RemoteServerInfo
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")
        result = svc.transfer_queue(server)
        assert not result.ok
        assert result.code == "EMPTY_QUEUE"

    def test_transfer_local_not_paused_on_remote_failure(self):
        """Critical: if remote fails, local playback MUST NOT be paused."""
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        pause_called = False

        def pause_local():
            nonlocal pause_called
            pause_called = True

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1"], 0, 0.0),
            pause_local=pause_local,
        )
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen", side_effect=OSError("transfer failed")):
            result = svc.transfer_queue(server)

        assert not result.ok
        assert not pause_called, "Local playback was paused despite remote failure!"

    def test_transfer_success_pauses_local(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        import json
        pause_called = False

        def pause_local():
            nonlocal pause_called
            pause_called = True

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1"], 0, 5000.0),
            pause_local=pause_local,
        )
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                m = MagicMock()
                m.status = 200
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "playback/state" in url:
                    m.read.return_value.decode.return_value = json.dumps({"state": "playing"})
                else:
                    m.read.return_value.decode.return_value = json.dumps({"ok": True})
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side
            result = svc.transfer_queue(server)

        assert result.ok
        assert pause_called, "Local playback was NOT paused after successful transfer"

    def test_auto_import_before_transfer(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        import json

        def resolve(tid):
            return f"/real/path/{tid}.flac"

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1", "t2"], 0, 0.0),
            resolve_track=resolve,
        )
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch.object(svc._import, "create_session",
                          return_value=type("R", (), {"ok": True, "data": {"session_id": "s1"}})()), \
             patch.object(svc._import, "upload_track",
                          return_value=type("R", (), {"ok": True})()), \
             patch.object(svc._import, "commit",
                          return_value=type("R", (), {"ok": True, "data": {"uploaded": 2}})()), \
             patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                m = MagicMock()
                m.status = 200
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "playback/state" in url:
                    m.read.return_value.decode.return_value = json.dumps({"state": "playing"})
                else:
                    m.read.return_value.decode.return_value = json.dumps({"ok": True})
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side
            result = svc.transfer_queue(server, auto_import=True, require_playing=False)

        assert result.ok


class TestTrackIdentityFullHash:
    def test_content_hash_present(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService,
        )
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"test_content" * 1000)
            path = f.name
        try:
            svc = TrackIdentityService()
            result = svc.compute(path, local_track_id="t1")
            assert result.ok
            ident = result.data
            assert len(ident.quick_hash) == 32
            assert len(ident.content_hash) == 64
            assert ident.quick_hash != ident.content_hash
        finally:
            os.unlink(path)

    def test_preflight_payload_includes_both_hashes(self):
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentityService, TrackIdentity,
        )
        svc = TrackIdentityService()
        ident = TrackIdentity(
            local_track_id="t1",
            quick_hash="abc123",
            content_hash="full_hash_64chars" + "x" * 49,
            file_size=1000,
        )
        payload = svc.identity_to_preflight(ident)
        assert payload["local_track_id"] == "t1"
        assert payload["quick_hash"] == "abc123"
        assert len(payload["content_hash"]) >= 30
        assert "filepath" not in payload


class TestUploadMapping:
    def test_upload_reads_remote_track_id(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")
        r1 = svc.create_session(server, ["t1"])
        sid = r1.data["session_id"]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = json.dumps({
                "remote_track_id": "rt_abc",
            })
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            r2 = svc.upload_track(sid, "t1", local_data=b"data")
            assert r2.ok
            assert r2.data["remote_track_id"] == "rt_abc"
            assert r2.data["mapping_status"] == "confirmed"

    def test_upload_mapping_unconfirmed(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")
        r1 = svc.create_session(server, ["t1"])
        sid = r1.data["session_id"]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = "{}"
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            r2 = svc.upload_track(sid, "t1", local_data=b"data")
            assert r2.ok
            assert r2.data["mapping_status"] == "MAPPING_UNCONFIRMED"

    def test_upload_mapping_empty_response(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")
        r1 = svc.create_session(server, ["t1"])
        sid = r1.data["session_id"]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = ""
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            r2 = svc.upload_track(sid, "t1", local_data=b"data")
            assert r2.ok
            assert r2.data["mapping_status"] == "MAPPING_UNCONFIRMED"


class TestPreflightContract:
    def test_new_contract(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch.object(svc, "_call_preflight", return_value={
            "results": [
                {"local_track_id": "t1", "status": "exists",
                 "remote_track_id": "rt1"},
            ],
        }):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok
            assert result.data["t1"]["remote_id"] == "rt1"
            assert result.data["t1"]["status"] == "exists"

    def test_legacy_contract(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch.object(svc, "_call_preflight", return_value={
            "results": [
                {"local_track_id": "t1", "exists": True,
                 "remote_track_id": "rt1"},
            ],
        }):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok
            assert result.data["t1"]["remote_id"] == "rt1"

    def test_contract_mismatch_missing_results(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch.object(svc, "_call_preflight", return_value={
            "unknown_format": True,
        }):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert not result.ok
            assert result.code == "PREFLIGHT_CONTRACT_MISMATCH"

    def test_fallback_when_404(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch.object(svc, "_call_preflight", return_value=None):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(server, ids)
            assert result.ok
            assert result.data["t1"]["exists"] is False


class TestContinueOnServerDeep:
    def test_does_not_pause_before_remote_playing(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        import json
        pause_called = False

        def pause_local():
            nonlocal pause_called
            pause_called = True

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1"], 0, 0.0),
            pause_local=pause_local,
        )
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side_effect(req, **kw):
                mock_resp = MagicMock()
                mock_resp.status = 200
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "queue/transfer" in url:
                    mock_resp.read.return_value.decode.return_value = json.dumps({"ok": True})
                elif "playback/control" in url:
                    raise OSError("remote play failed")
                else:
                    mock_resp.read.return_value.decode.return_value = json.dumps({})
                return MagicMock(__enter__=lambda x: mock_resp)
            mock_urlopen.side_effect = side_effect

            result = svc.transfer_queue(
                server, track_ids=["t1"], require_playing=False,
            )
            assert not pause_called, "Local was paused despite remote play failure!"
            assert result.ok

    def test_fallback_without_queue_transfer(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        from urllib.error import HTTPError
        import json

        call_log = []

        call_log = []

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1", "t2"], 1, 15000.0),
        )
        server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side_effect(req, data=None, **kw):
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.read.return_value.decode.return_value = json.dumps({})

                if "queue/transfer" in url:
                    raise HTTPError(url, 404, "Not Found", {}, None)
                if "queue/items" in url:
                    call_log.append("queue/items")
                elif "queue/jump" in url:
                    call_log.append("queue/jump")
                elif "seek" in url:
                    call_log.append("seek")
                return MagicMock(__enter__=lambda x: mock_resp)
            mock_urlopen.side_effect = side_effect

            result = svc.transfer_queue(
                server, require_playing=False,
            )
            assert result.ok
            assert "queue/items" in call_log, "Fallback queue/items not called"
            assert "queue/jump" in call_log, "Fallback queue/jump not called"

    def test_import_missing_uses_resolved_filepath(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from integrations.michi_link.client import RemoteServerInfo
        import json
        import tempfile
        import os

        # Create a real temp file so filepath exists
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"x" * 1024)
            real_path = f.name

        def resolve(tid):
            return real_path

        try:
            svc = ContinueOnServerService(
                queue_provider=lambda: ([real_path], 0, 0.0),
                resolve_track=resolve,
            )
            server = RemoteServerInfo(host="10.0.0.1", port=53318, device_token="tok")

            with patch.object(svc._import, "create_session",
                              return_value=type("R", (), {"ok": True, "data": {"session_id": "s1"}})()), \
                 patch.object(svc._import, "upload_track",
                              return_value=type("R", (), {"ok": True})()) as mock_upload, \
                 patch.object(svc._import, "commit",
                              return_value=type("R", (), {"ok": True, "data": {"uploaded": 1}})()), \
                 patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value.__enter__.return_value.read.return_value.decode.return_value = \
                    json.dumps({"ok": True})
                mock_urlopen.return_value.__enter__.return_value.status = 200

                result = svc.transfer_queue(server, track_ids=[real_path],
                                            auto_import=True, require_playing=False)
                assert result.ok
                _, kwargs = mock_upload.call_args
                assert kwargs.get("local_filepath") == real_path
        finally:
            os.unlink(real_path)
