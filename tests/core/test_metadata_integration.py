"""Integration tests for Metadata Core V2 — ServiceContainer, Bridge, and Settings."""

import pytest
import tempfile
import os

from core.metadata_service import MetadataService


@pytest.fixture
def svc():
    return MetadataService()


class TestMetadataService:
    def test_probe_nonexistent(self, svc):
        result = svc.probe("/nonexistent/file.mp3")
        assert result.ok is False
        assert result.code == "FILE_NOT_FOUND"

    def test_probe_empty_path(self, svc):
        result = svc.probe("")
        assert result.ok is False

    def test_probe_unsupported_format(self, svc):
        result = svc.probe("test.xyz")
        assert result.ok is False

    def test_probe_valid_format(self, svc):
        fd, path = tempfile.mkstemp(suffix=".flac")
        os.close(fd)
        result = svc.probe(path)
        os.unlink(path)
        assert result.ok is True

    def test_read_nonexistent(self, svc):
        result = svc.read("/nonexistent/file.flac")
        assert result.ok is False

    def test_health(self, svc):
        h = svc.health()
        assert h["available"] is True
        assert h["has_library"] is False

    def test_create_confirmation_token(self, svc):
        review_id = svc.create_confirmation_token("/music/song.flac", 3)
        assert len(review_id) == 8
        assert review_id in svc._pending_tokens

    def test_confirm_and_apply_invalid_token(self, svc):
        from metadata.tag_model import TrackTags
        tags = TrackTags(filepath="test.flac")
        result = svc.confirm_and_apply("invalid", tags)
        assert result.ok is False
        assert result.code == "INVALID_TOKEN"

    def test_confirm_and_apply_double_use(self, svc):
        from metadata.tag_model import TrackTags
        review_id = svc.create_confirmation_token("/music/song.flac", 1)
        tags = TrackTags(filepath="test.flac")
        svc._pending_tokens[review_id].used = True
        result = svc.confirm_and_apply(review_id, tags)
        assert result.ok is False
        assert result.code in ("TOKEN_EXPIRED", "INVALID_TOKEN")

    def test_inspect_track_no_library(self, svc):
        result = svc.inspect_track(1)
        assert result.ok is False
        assert result.code == "LIBRARY_UNAVAILABLE"

    def test_shutdown_clears_tokens(self, svc):
        svc.create_confirmation_token("/music/song.flac", 1)
        assert len(svc._pending_tokens) == 1
        svc.shutdown()
        assert len(svc._pending_tokens) == 0


class TestConfirmationService:
    def test_request_and_approve(self):
        from core.confirmation_service import ConfirmationService
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac", field_count=3)
        assert req.token is not None
        assert not req.resolved
        approved = cs.approve(req.token)
        assert approved is not None
        assert approved.approved is True

    def test_reject(self):
        from core.confirmation_service import ConfirmationService
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac")
        assert cs.reject(req.token) is True
        assert cs.approve(req.token) is None

    def test_expired_token(self):
        from core.confirmation_service import ConfirmationService, ConfirmationRequest
        cs = ConfirmationService()
        req = ConfirmationRequest("op-1", "/music/song.flac", "test", expiry_s=0)
        cs._pending[req.token] = req
        import time
        time.sleep(0.01)
        assert cs.approve(req.token) is None

    def test_revoke(self):
        from core.confirmation_service import ConfirmationService
        cs = ConfirmationService()
        req = cs.request("op-1", "/music/song.flac")
        cs.revoke("op-1")
        assert cs.approve(req.token) is None


class TestMetadataServiceWithLibrary:
    def test_with_mock_library(self):
        class MockLibraryRepo:
            def get_track(self, track_id):
                if track_id == 1:
                    class Track:
                        filepath = "/tmp/test.flac"
                    return Track()
                return None

        svc = MetadataService(library_repo=MockLibraryRepo())
        result = svc.inspect_track(1)
        assert result.ok is False  # file doesn't exist
        result = svc.inspect_track(999)
        assert result.ok is False
        assert result.code == "TRACK_NOT_FOUND"
