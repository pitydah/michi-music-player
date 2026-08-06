"""Contract compatibility tests: Player ↔ Micro Server.

Tests each endpoint against official michi-link contract examples.
Verifies new format, legacy format, unsupported (404), and edge cases.
"""
from __future__ import annotations

import hashlib
import json
import os
from unittest.mock import MagicMock, patch

from integrations.michi_link.client import RemoteServerInfo

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures", "micro_contract")


def _load(name: str) -> dict:
    path = os.path.normpath(os.path.join(FIXTURES, name))
    with open(path) as f:
        return json.load(f)


def _make_server() -> RemoteServerInfo:
    return RemoteServerInfo(
        host="10.0.0.100", port=53318, alias="Micro",
        server_device_id="micro_001", requires_pairing=True,
        device_token="tok_abc", device_id="player_d1",
    )


def _session_urlopen():
    """urlopen side effect answering import/session/create (Slice 7: sessions
    are created on the server, so tests must answer the endpoint)."""
    def side(req, **kw):
        url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
        assert "import/session/create" in url, f"Unexpected URL: {url}"
        m = MagicMock()
        m.status = 200
        m.read.return_value = json.dumps({
            "session_id": "sess_01", "expires_at": 9999999999.0,
            "state": "pending",
        }).encode()
        return MagicMock(__enter__=lambda x: m)
    return side


class TestPreflightContract:
    def test_new_contract(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        response = _load("preflight_new.json")
        with patch.object(svc, "_call_preflight", return_value=response):
            ids = [TrackIdentity(local_track_id="t1"),
                   TrackIdentity(local_track_id="t2")]
            result = svc.preflight(_make_server(), ids)
            assert result.ok
            assert result.data["t1"]["exists"] is True
            assert result.data["t1"]["remote_id"] == "rt1"
            assert result.data["t2"]["exists"] is False

    def test_legacy_contract(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        response = _load("preflight_legacy.json")
        with patch.object(svc, "_call_preflight", return_value=response):
            ids = [TrackIdentity(local_track_id="t1"),
                   TrackIdentity(local_track_id="t2")]
            result = svc.preflight(_make_server(), ids)
            assert result.ok
            assert result.data["t1"]["exists"] is True
            assert result.data["t2"]["exists"] is False

    def test_new_contract_no_michi_track_id_fallback(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        response = _load("preflight_new.json")
        # Remove michi_track_id to test content_hash fallback matching
        for r in response["results"]:
            r.pop("michi_track_id", None)
        with patch.object(svc, "_call_preflight", return_value=response):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(_make_server(), ids)
            assert result.ok

    def test_unsupported_404(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        with patch.object(svc, "_call_preflight", return_value=None):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(_make_server(), ids)
            assert result.ok
            assert result.data["t1"]["exists"] is False

    def test_mismatch_missing_results(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from integrations.michi_link.services.track_identity_service import (
            TrackIdentity,
        )
        svc = ImportToServerService()
        with patch.object(svc, "_call_preflight", return_value={"unknown": True}):
            ids = [TrackIdentity(local_track_id="t1")]
            result = svc.preflight(_make_server(), ids)
            assert not result.ok
            assert result.code == "PREFLIGHT_CONTRACT_MISMATCH"


class TestUploadContract:
    def test_upload_returns_remote_track_id(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        payload = _load("upload_result.json")
        payload["checksum"] = hashlib.sha256(b"data").hexdigest()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = json.dumps(payload)
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.upload_track(sid, "t1", local_data=b"data")
            assert result.ok
            assert result.data["remote_track_id"] == "rt1"
            assert result.data["mapping_status"] == "confirmed"

    def test_upload_mapping_unconfirmed(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = "{}"
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.upload_track(sid, "t1", local_data=b"d")
            assert result.ok
            assert result.data["mapping_status"] == "MAPPING_UNCONFIRMED"

    def test_upload_empty_response(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value.decode.return_value = ""
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.upload_track(sid, "t1", local_data=b"d")
            assert result.ok
            assert result.data["mapping_status"] == "MAPPING_UNCONFIRMED"

    def test_upload_http_error(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from urllib.error import HTTPError
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://micro/api/v1/import/track/upload", 500,
                "Server Error", {}, None,
            )
            result = svc.upload_track(sid, "t1", local_data=b"d")
            assert not result.ok
            assert result.code in ("UPLOAD_FAILED", "HTTP_500")


class TestCommitContract:
    def test_commit_returns_mapping(self):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1", "t2"])
        sid = r1.data["session_id"]

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                m = MagicMock()
                if "session/status" in url:
                    m.read.return_value.decode.return_value = json.dumps({
                        "session_id": "s1", "state": "committed",
                        "uploaded_tracks": 2, "artwork_count": 0,
                        "playlist_count": 0,
                    })
                else:
                    m.read.return_value.decode.return_value = json.dumps(
                        _load("commit_mapping.json"))
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side

            # Manually mark as uploaded
            svc._sessions[sid].uploaded = 2
            result = svc.commit(sid)
            assert result.ok
            assert "mapping" in result.data
            assert len(result.data["mapping"]) >= 2
            assert result.data["readback_verified"] is True

    def test_commit_real_endpoint_fails_gracefully(self):
        """Slice 7: commit is no longer locally faked — a failed server commit
        is reported explicitly (this test documents the old nominal-success
        behaviour being replaced)."""
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        from urllib.error import HTTPError
        svc = ImportToServerService()
        with patch("urllib.request.urlopen", side_effect=_session_urlopen()):
            r1 = svc.create_session(_make_server(), ["t1"])
        sid = r1.data["session_id"]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://micro/api/v1/import/session/commit",
                404, "Not Found", {}, None,
            )
            svc._sessions[sid].uploaded = 1
            result = svc.commit(sid)
            # Commit must NOT succeed silently when the server rejects it.
            assert not result.ok
            assert result.code in ("COMMIT_FAILED", "IMPORT_ENDPOINTS_MISSING")


class TestQueueTransferContract:
    def test_transfer_exists(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1", "t2"], 0, 0),
        )
        payload = _load("queue_transfer_result.json")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value.decode.return_value = json.dumps(payload)
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = svc.transfer_queue(_make_server(), track_ids=["t1", "t2"],
                                        require_playing=False)
            assert result.ok

    def test_transfer_404_uses_fallback(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        from urllib.error import HTTPError
        call_log = []
        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1", "t2"], 1, 15000),
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                m = MagicMock()
                m.status = 200
                m.read.return_value.decode.return_value = json.dumps({})
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "queue/transfer" in url:
                    raise HTTPError(url, 404, "Not Found", {}, None)
                if "queue/items" in url:
                    call_log.append("items")
                elif "queue/jump" in url:
                    call_log.append("jump")
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side
            result = svc.transfer_queue(_make_server(), require_playing=False)
            assert result.ok
            assert "items" in call_log
            assert "jump" in call_log


class TestCompatibilityReport:
    def test_report_structure(self):
        from integrations.michi_link.services.compatibility_report import (
            PlayerMicroCompatibilityReport,
        )
        report = PlayerMicroCompatibilityReport()
        server = _make_server()

        with patch.object(report._client, "discover", return_value=None), \
             patch("urllib.request.urlopen") as mock_urlopen:
            from urllib.error import HTTPError
            mock_urlopen.side_effect = HTTPError(
                "http://test", 404, "Not Found", {}, None,
            )
            result = report.generate(server)
        assert isinstance(result, dict)

    def test_preflight_ok_constant(self):
        from integrations.michi_link.services.diagnostics_service import (
            CONTRACT_OK, CONTRACT_PARTIAL, CONTRACT_MISMATCH,
            ENDPOINT_MISSING, FALLBACK_AVAILABLE,
        )
        assert CONTRACT_OK == "CONTRACT_OK"
        assert CONTRACT_PARTIAL == "CONTRACT_PARTIAL"
        assert CONTRACT_MISMATCH == "CONTRACT_MISMATCH"
        assert ENDPOINT_MISSING == "ENDPOINT_MISSING"
        assert FALLBACK_AVAILABLE == "FALLBACK_AVAILABLE"


class TestRemotePlaybackConfirmation:
    def test_playing_confirmed_pauses_local(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        pause_called = False
        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1"], 0, 0),
            pause_local=lambda: setattr(__import__("builtins"), "_test_pause",
                                        True),
        )
        pause_called = False

        def pause():
            nonlocal pause_called
            pause_called = True

        svc._pause_local = pause

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                m = MagicMock()
                m.status = 200
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "playback/state" in url:
                    m.read.return_value.decode.return_value = json.dumps(
                        _load("playback_state_playing.json"))
                else:
                    m.read.return_value.decode.return_value = json.dumps({"ok": True})
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side
            result = svc.transfer_queue(_make_server(), track_ids=["t1"])
            assert result.ok
            assert pause_called, "Local was NOT paused after PLAYING confirmed"

    def test_playing_not_confirmed_does_not_pause(self):
        from integrations.michi_link.services.continue_on_server_service import (
            ContinueOnServerService,
        )
        pause_called = False

        def pause():
            nonlocal pause_called
            pause_called = True

        svc = ContinueOnServerService(
            queue_provider=lambda: (["t1"], 0, 0),
            pause_local=pause,
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side(req, **kw):
                m = MagicMock()
                m.status = 200
                url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
                if "playback/state" in url:
                    m.read.return_value.decode.return_value = json.dumps(
                        _load("playback_state_paused.json"))
                else:
                    m.read.return_value.decode.return_value = json.dumps({"ok": True})
                return MagicMock(__enter__=lambda x: m)
            mock_urlopen.side_effect = side
            result = svc.transfer_queue(_make_server(), track_ids=["t1"])
            assert result.ok
            assert not pause_called, "Local WAS paused despite state != PLAYING"
