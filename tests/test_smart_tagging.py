"""Tests for SmartTaggingService — suggestions, confidence, batch."""
from unittest.mock import MagicMock, patch

import pytest


class TestSmartTagging:
    @pytest.fixture
    def svc(self):
        from core.smart_tagging_service import SmartTaggingService
        return SmartTaggingService()

    def test_not_available_without_recognition(self, svc):
        assert not svc.available
        result = svc.identify("/test/file.flac")
        assert not result["ok"]

    def test_cancel(self, svc):
        svc.cancel()
        result = svc.batch_identify(["/test/a.flac", "/test/b.flac"])
        assert result.get("cancelled")

    def test_health(self, svc):
        health = svc.health()
        assert not health["available"]

    @pytest.fixture
    def svc_with_recognition(self):
        from core.smart_tagging_service import SmartTaggingService
        mock_rec = MagicMock()
        mock_rec.identify.return_value = {
            "title": "Test Song", "artist": "Test Artist",
            "album": "Test Album", "confidence": 0.85, "source": "musicbrainz"
        }
        return SmartTaggingService(recognition_service=mock_rec)

    def test_identify_with_recognition(self, svc_with_recognition):
        with patch("metadata.tag_reader.read_tags") as mock_read:
            from metadata.tag_model import TrackTags
            mock_read.return_value = TrackTags(filepath="/test/file.flac")
            result = svc_with_recognition.identify("/test/file.flac")
            assert result["ok"]
            assert len(result["suggestions"]) >= 0
            assert result["overall_confidence"] == 0.85

    def test_accept_suggestion_no_file(self, svc_with_recognition):
        result = svc_with_recognition.accept_suggestion("/nonexistent.flac", "title", "New")
        assert not result["ok"]

    def test_batch_identify(self, svc_with_recognition):
        with patch("metadata.tag_reader.read_tags") as mock_read:
            from metadata.tag_model import TrackTags
            mock_read.return_value = TrackTags(filepath="/test/file.flac")
            result = svc_with_recognition.batch_identify(["/test/a.flac", "/test/b.flac"])
            assert result["ok"]
            assert result["count"] == 2
