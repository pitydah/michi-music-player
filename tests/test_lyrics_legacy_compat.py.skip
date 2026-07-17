"""Test legacy LrcLibClient compatibility with the new core."""

import json
from unittest.mock import MagicMock, patch

from lyrics.lrclib_client import LrcLibClient, LyricLine, LyricsResult


class TestLegacyLrcLibClient:
    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_synced(self, mock_urlopen):
        client = LrcLibClient()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "[01:30.50]Hello world\n[02:00.00]Second line",
            "plainLyrics": "Hello world\nSecond line",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = client.get_lyrics("Test Song", "Test Artist")
        assert result is not None
        assert result.source == "lrclib.net"
        assert len(result.lines) == 2
        assert result.lines[0].text == "Hello world"

    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_none_on_404(self, mock_urlopen):
        from urllib.error import HTTPError
        client = LrcLibClient()
        mock_urlopen.side_effect = HTTPError("http://lrclib.net", 404, "Not Found", {}, None)
        result = client.get_lyrics("Nonexistent", "Nobody")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_none_on_timeout(self, mock_urlopen):
        from urllib.error import URLError
        client = LrcLibClient()
        mock_urlopen.side_effect = URLError("timed out")
        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_none_on_invalid_json(self, mock_urlopen):
        client = LrcLibClient()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx
        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_caching_returns_cached_result(self, mock_urlopen):
        client = LrcLibClient()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "[01:00.00]Hello",
            "plainLyrics": "Hello",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result1 = client.get_lyrics("Song", "Artist")
        assert result1 is not None

        mock_urlopen.reset_mock()
        result2 = client.get_lyrics("Song", "Artist")
        assert result2 is result1
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_search_returns_results(self, mock_urlopen):
        client = LrcLibClient()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {"syncedLyrics": "[01:00.00]Hello", "plainLyrics": "Hello"},
            {"syncedLyrics": "", "plainLyrics": "World"},
        ]).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        results = client.search("test query")
        assert len(results) >= 1

    @patch("urllib.request.urlopen")
    def test_search_returns_empty_on_error(self, mock_urlopen):
        client = LrcLibClient()
        mock_urlopen.side_effect = Exception("fail")
        results = client.search("test")
        assert results == []

    def test_lyric_line_fields(self):
        line = LyricLine(timestamp=42.5, text="Hello")
        assert line.timestamp == 42.5
        assert line.text == "Hello"

    def test_lyrics_result_fields(self):
        r = LyricsResult()
        assert r.lines == []
        assert r.plain == ""
        assert r.source == ""

    def test_parse_lrc_standard(self):
        lrc = "[01:30.50]First line\n[02:00.00]Second line"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 2
        assert lines[0].timestamp == 90.5 or abs(lines[0].timestamp - 90.05) < 0.1
        assert lines[0].text == "First line"

    def test_parse_lrc_sorts(self):
        lrc = "[03:00.00]Third\n[01:00.00]First\n[02:00.00]Second"
        lines = LrcLibClient._parse_lrc(lrc)
        assert lines[0].text == "First"
        assert lines[1].text == "Second"
        assert lines[2].text == "Third"

    def test_parse_lrc_skips_non_lyric(self):
        lrc = "[01:00.00]Valid\nNot a lyric\n[02:00.00]Also valid"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 2
