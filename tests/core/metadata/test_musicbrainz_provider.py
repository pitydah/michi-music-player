from unittest.mock import MagicMock, patch

from integrations.musicbrainz.provider import MusicBrainzProvider


class TestMusicBrainzProvider:
    def test_search_artist_empty_query(self):
        provider = MusicBrainzProvider()
        result = provider.search_artist("")
        assert result.ok is False

    @patch("urllib.request.urlopen")
    def test_search_artist(self, mock_urlopen):
        provider = MusicBrainzProvider()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"artists": [{"id": "abc", "name": "Test Artist"}]}'
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = provider.search_artist("Test Artist")
        assert result.ok is True

    @patch("urllib.request.urlopen")
    def test_lookup_recording(self, mock_urlopen):
        provider = MusicBrainzProvider()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"id": "mbid-123", "title": "Test Song"}'
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = provider.lookup_recording("mbid-123")
        assert result.ok is True
        assert result.data["response"]["id"] == "mbid-123"

    def test_to_document(self):
        provider = MusicBrainzProvider()
        data = {"id": "mbid-456", "title": "Song Title"}
        doc = provider.to_document(data)
        assert doc.track.title == "Song Title"
        assert doc.track.musicbrainz_recording_id == "mbid-456"

    def test_close(self):
        provider = MusicBrainzProvider()
        provider.close()
