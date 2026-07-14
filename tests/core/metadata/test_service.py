import pytest

from core.metadata.service import MetadataService
from core.metadata.models import (
    MetadataDocument, TrackMetadata,
)
from core.metadata.enums import MetadataErrorCode


@pytest.fixture
def service():
    svc = MetadataService()
    return svc


class TestMetadataService:
    def test_probe_nonexistent(self, service):
        result = service.probe("/nonexistent/file.mp3")
        assert result.ok is False
        assert "FILE_NOT_FOUND" in result.code or result.code == MetadataErrorCode.FILE_NOT_FOUND.value or "FILE_NOT_FOUND" in result.code.upper()

    def test_probe_empty_path(self, service):
        result = service.probe("")
        assert result.ok is False

    def test_probe_unsupported_format(self, service):
        result = service.probe("test.xyz")
        assert result.ok is False

    def test_health(self, service):
        h = service.health()
        assert h["formats"] >= 5
        assert h["readable"] >= 5
        assert h["writable"] >= 4

    def test_normalize(self, service):
        doc = MetadataDocument(track=TrackMetadata(title="  Test  "))
        normalized = service.normalize(doc)
        assert normalized.track.title == "Test"

    def test_read_many_empty(self, service):
        results = service.read_many([])
        assert results == []

    def test_read_many_cancelled(self, service):
        from core.metadata.cancellation import MetadataCancellationToken
        token = MetadataCancellationToken()
        token.cancel()
        results = service.read_many(["/nonexistent/1.flac", "/nonexistent/2.flac"], token=token)
        assert len(results) == 1
        assert results[0].ok is False

    def test_batch_apply_empty(self, service):
        results = service.batch_apply([])
        assert results == []

    def test_batch_apply_cancelled(self, service):
        from core.metadata.cancellation import MetadataCancellationToken
        token = MetadataCancellationToken()
        token.cancel()
        results = service.batch_apply(
            [("/nonexistent.flac", MetadataDocument(), [])], token=token,
        )
        assert len(results) == 1
        assert results[0].ok is False
