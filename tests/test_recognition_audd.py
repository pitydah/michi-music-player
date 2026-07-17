"""Tests for AudD recognition provider."""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestAudDProvider:
    def make_provider(self):
        from recognition.providers.audd import AudDProvider
        p = AudDProvider()
        p.api_key = "test_audd_key"
        return p

    @patch("urllib.request.urlopen")
    def test_identify_with_api_key(self, mock_urlopen):
        p = self.make_provider()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "status": "success",
            "result": {"title": "T", "artist": "A"}
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        p.identify(sample_bytes=b"\x00\x01\x02")
        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data)
        assert body["api_token"] == "test_audd_key"

    @patch("urllib.request.urlopen")
    def test_identify_returns_match(self, mock_urlopen):
        p = self.make_provider()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "status": "success",
            "result": {
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "song_link": "http://audd.io/song/1",
                "isrc": "USABC1234567",
            }
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = p.identify(sample_bytes=b"\x00\x01\x02")
        assert result is not None
        assert result["title"] == "Test Song"
        assert result["artist"] == "Test Artist"
        assert result["album"] == "Test Album"
        assert result["isrc"] == "USABC1234567"
        assert result["confidence"] == 0.9
        assert result["provider"] == "audd"

    def test_identify_rate_limit(self):
        from urllib.error import HTTPError
        p = self.make_provider()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://api.audd.io", 429, "Rate Limit Exceeded", {}, None)
            result = p.identify(sample_bytes=b"\x00\x01\x02")
            assert result is None

    def test_audio_base64_encoding(self):
        p = self.make_provider()
        sample = b"test_audio_bytes_12345"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "status": "success",
                "result": {"title": "T", "artist": "A"}
            }).encode()
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_ctx

            p.identify(sample_bytes=sample)
            import base64
            request = mock_urlopen.call_args[0][0]
            body = json.loads(request.data)
            expected_b64 = base64.b64encode(sample).decode()
            assert body["audio"] == expected_b64
