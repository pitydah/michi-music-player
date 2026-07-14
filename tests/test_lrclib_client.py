"""Tests for LRC Lyrics Client — fetches synced lyrics from lrclib.net."""
import json
import time
from unittest.mock import MagicMock, patch


from lyrics.lrclib_client import LrcLibClient, LyricLine, LyricsResult


class TestLyricLine:
    def test_basic(self):
        line = LyricLine(timestamp=42.5, text="Hello")
        assert line.timestamp == 42.5
        assert line.text == "Hello"


class TestLyricsResult:
    def test_defaults(self):
        r = LyricsResult()
        assert r.lines == []
        assert r.plain == ""
        assert r.source == ""

    def test_with_values(self):
        lines = [LyricLine(1.0, "a")]
        r = LyricsResult(lines=lines, plain="a\nb", source="lrclib.net")
        assert len(r.lines) == 1
        assert r.plain == "a\nb"


class TestLrcLibClient:
    def make_client(self):
        client = LrcLibClient()
        client._cache = {}
        return client

    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_synced(self, mock_urlopen):
        client = self.make_client()
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
        assert abs(result.lines[0].timestamp - 90.5) < 0.1
        assert result.lines[1].text == "Second line"
        assert result.lines[1].timestamp == 120.0

    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_plain_when_no_synced(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "",
            "plainLyrics": "Line one\nLine two\nLine three",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = client.get_lyrics("Test Song", "Test Artist")
        assert result is not None
        assert result.plain == "Line one\nLine two\nLine three"

    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_none_on_404(self, mock_urlopen):
        from urllib.error import HTTPError
        client = self.make_client()
        mock_urlopen.side_effect = HTTPError(
            "http://lrclib.net", 404, "Not Found", {}, None)

        result = client.get_lyrics("Nonexistent", "Nobody")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_returns_none_on_500(self, mock_urlopen):
        from urllib.error import HTTPError
        client = self.make_client()
        mock_urlopen.side_effect = HTTPError(
            "http://lrclib.net", 500, "Server Error", {}, None)

        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_none_on_timeout(self, mock_urlopen):
        from urllib.error import URLError
        client = self.make_client()
        mock_urlopen.side_effect = URLError("timed out")

        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_none_on_invalid_json(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_get_lyrics_none_on_empty_response(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "",
            "plainLyrics": "",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = client.get_lyrics("Test", "Artist")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_caching_returns_cached_result(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "[01:00.00]Hello",
            "plainLyrics": "Hello",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        # First call hits network
        result1 = client.get_lyrics("Song", "Artist")
        assert result1 is not None

        # Second call should use cache, not network
        mock_urlopen.reset_mock()
        result2 = client.get_lyrics("Song", "Artist")
        assert result2 is result1
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_caching_returns_none_for_404(self, mock_urlopen):
        from urllib.error import HTTPError
        client = self.make_client()
        mock_urlopen.side_effect = HTTPError(
            "http://lrclib.net", 404, "Not Found", {}, None)

        # First call misses
        result1 = client.get_lyrics("Missing", "Nobody")
        assert result1 is None

        # Second call should return cached None
        result2 = client.get_lyrics("Missing", "Nobody")
        assert result2 is None
        # Network not called again
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_cache_key_case_insensitive(self, mock_urlopen):
        client = self.make_client()
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

        result2 = client.get_lyrics("song", "artist")
        assert result2 is result1
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_request_includes_album_and_duration(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "",
            "plainLyrics": "lyrics",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        client.get_lyrics("Song", "Artist", album="Album", duration=240.0)
        url = mock_urlopen.call_args[0][0].full_url
        assert "album_name=Album" in url
        assert "duration=240" in url
        assert "artist_name=Artist" in url
        assert "track_name=Song" in url

    @patch("urllib.request.urlopen")
    def test_search_returns_results(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([
            {
                "syncedLyrics": "[01:00.00]Hello",
                "plainLyrics": "Hello",
            },
            {
                "syncedLyrics": "",
                "plainLyrics": "World",
            },
        ]).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        results = client.search("test query")
        assert len(results) == 2
        assert results[0].lines[0].text == "Hello"
        assert results[1].plain == "World"

    @patch("urllib.request.urlopen")
    def test_search_returns_empty_on_error(self, mock_urlopen):
        client = self.make_client()
        mock_urlopen.side_effect = Exception("fail")

        results = client.search("test")
        assert results == []

    @patch("urllib.request.urlopen")
    def test_throttle_waits_one_second(self, mock_urlopen):
        client = self.make_client()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "syncedLyrics": "",
            "plainLyrics": "lyrics",
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        client._throttle_ts = time.monotonic()  # Set to now so next call waits
        start = time.monotonic()
        client.get_lyrics("Song", "Artist")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.9  # Should have waited ~1s


class TestParseLrc:
    def test_parse_standard_format(self):
        lrc = "[01:30.50]First line\n[02:00.00]Second line"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 2
        assert abs(lines[0].timestamp - 90.5) < 0.1
        assert lines[0].text == "First line"
        assert lines[1].timestamp == 120.0
        assert lines[1].text == "Second line"

    def test_parse_short_format(self):
        lrc = "[01:30]No millis"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 1
        assert lines[0].timestamp == 90.0

    def test_parse_multi_timestamp(self):
        lrc = "[01:00.00][01:30.00]Same text"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 2
        assert lines[0].timestamp == 60.0
        assert lines[1].timestamp == 90.0
        assert lines[0].text == "Same text"
        assert lines[1].text == "Same text"

    def test_parse_skips_non_lyric_lines(self):
        lrc = "[01:00.00]Valid\nNot a lyric line\n[02:00.00]Also valid"
        lines = LrcLibClient._parse_lrc(lrc)
        assert len(lines) == 2

    def test_parse_sorts_by_timestamp(self):
        lrc = "[03:00.00]Third\n[01:00.00]First\n[02:00.00]Second"
        lines = LrcLibClient._parse_lrc(lrc)
        assert lines[0].text == "First"
        assert lines[1].text == "Second"
        assert lines[2].text == "Third"
