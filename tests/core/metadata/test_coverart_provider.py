from unittest.mock import MagicMock, patch

from integrations.coverart.provider import CoverArtProvider


class TestCoverArtProvider:
    def test_resolve_empty_mbid(self):
        provider = CoverArtProvider()
        result = provider.resolve("")
        assert result.ok is False

    @patch("urllib.request.urlopen")
    def test_resolve_with_artwork(self, mock_urlopen):
        provider = CoverArtProvider()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"images": [{"id": "img-1", "image": "https://archive.org/img.jpg", "types": ["front_cover"]}]}'
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = provider.resolve("release-mbid-123")
        assert result.ok is True
        assert result.data["count"] == 1
        assert result.data["front_cover"] is not None

    def test_detect_mime(self):
        assert CoverArtProvider._detect_mime("http://example.com/img.jpg") == "image/jpeg"
        assert CoverArtProvider._detect_mime("http://example.com/img.png") == "image/png"
