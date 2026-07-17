"""Tests for SubsonicSource — wraps SubsonicClient as a MusicSource."""

import json
import hashlib
import random
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from sources.base_source import TrackRef
from sources.subsonic_source import SubsonicSource
from streaming.subsonic_client import SubsonicClient, ServerConfig


def make_server(**kwargs):
    return ServerConfig(
        name=kwargs.get("name", "Test Server"),
        url=kwargs.get("url", "http://localhost:4533"),
        username=kwargs.get("username", "user"),
        password=kwargs.get("password", "secret"),
        stype=kwargs.get("stype", "navidrome"),
    )


def make_client(server=None):
    if server is None:
        server = make_server()
    return SubsonicClient(server)


class TestSubsonicSourceInitializes:
    def test_subsonic_source_initializes(self):
        client = make_client()
        source = SubsonicSource(client)
        assert source._client is client
        assert source.can_stream(TrackRef(uri="http://example.com/track")) is True


class TestSearchReturnsResults:
    def test_search_returns_results(self):
        client = make_client()

        resp = {
            "searchResult3": {
                "song": [
                    {
                        "id": "123",
                        "title": "Test Song",
                        "artist": "Test Artist",
                        "album": "Test Album",
                        "duration": 180,
                        "year": 2024,
                        "coverArt": "cover1",
                        "track": 2,
                        "genre": "Rock",
                    }
                ]
            }
        }

        with patch.object(client, "_get", return_value=resp):
            source = SubsonicSource(client)
            results = source.search("test")

        assert len(results) == 1
        track = results[0]
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.duration == 180.0
        assert track.track_number == 2
        assert track.genre == "Rock"
        assert "cover1" in track.cover_path
        assert "123" in track.uri
        assert track.source_type == "navidrome"
        assert track.source_label == ""

    def test_search_returns_multiple_songs(self):
        client = make_client()

        resp = {
            "searchResult3": {
                "song": [
                    {"id": "1", "title": "Song A", "artist": "Art A",
                     "album": "Alb A", "duration": 200, "track": 1},
                    {"id": "2", "title": "Song B", "artist": "Art B",
                     "album": "Alb B", "duration": 250, "track": 3},
                ]
            }
        }

        with patch.object(client, "_get", return_value=resp):
            source = SubsonicSource(client)
            results = source.search("query")

        assert len(results) == 2
        assert results[0].title == "Song A"
        assert results[1].title == "Song B"

    def test_search_empty_result(self):
        client = make_client()

        resp = {"searchResult3": {"song": []}}

        with patch.object(client, "_get", return_value=resp):
            source = SubsonicSource(client)
            results = source.search("nonexistent")

        assert results == []

    def test_search_missing_search_result3(self):
        client = make_client()

        resp = {}

        with patch.object(client, "_get", return_value=resp):
            source = SubsonicSource(client)
            results = source.search("test")

        assert results == []


class TestSearchHandlesNetworkError:
    def test_http_500_returns_empty_list(self):
        client = make_client()

        with patch.object(client, "_get", side_effect=Exception("Server error (500)")):
            source = SubsonicSource(client)
            results = source.search("test")

        assert results == []

    def test_timeout_returns_empty_list(self):
        client = make_client()

        with patch.object(client, "_get", side_effect=Exception("timed out")):
            source = SubsonicSource(client)
            results = source.search("test")

        assert results == []

    def test_connection_refused_returns_empty_list(self):
        client = make_client()

        with patch.object(client, "_get", side_effect=Exception("Connection refused")):
            source = SubsonicSource(client)
            results = source.search("test")

        assert results == []

    def test_invalid_json_returns_empty_list(self):
        client = make_client()

        with patch.object(client, "_get", side_effect=Exception("Invalid response")):
            source = SubsonicSource(client)
            results = source.search("test")

        assert results == []


class TestAuthenticationToken:
    def test_authentication_token_sent_correctly(self):
        password = "secret"
        server = make_server(password=password)
        client = make_client(server)
        source = SubsonicSource(client)

        resp = {"searchResult3": {"song": []}}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                {"subsonic-response": resp}
            ).encode()
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_ctx

            source.search("test")

        assert mock_urlopen.call_count >= 1
        req = mock_urlopen.call_args[0][0]
        url = req.full_url

        assert "u=user" in url
        assert "&t=" in url
        assert "&s=" in url
        assert "v=1.16.0" in url
        assert "c=MichiMusicPlayer" in url
        assert "f=json" in url

        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        assert "t" in qs
        assert "s" in qs
        assert "u" in qs
        assert qs["u"] == ["user"]

        expected_token = hashlib.md5(
            (password + qs["s"][0]).encode("utf-8")
        ).hexdigest()
        assert qs["t"][0] == expected_token

    def test_query_parameter_included(self):
        client = make_client()
        source = SubsonicSource(client)

        resp = {"searchResult3": {"song": []}}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                {"subsonic-response": resp}
            ).encode()
            mock_ctx = MagicMock()
            mock_ctx.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_ctx

            source.search("Test Query")

        req = mock_urlopen.call_args[0][0]
        assert "query=Test+Query" in req.full_url
        assert "songCount=30" in req.full_url
        assert "artistCount=10" in req.full_url
        assert "albumCount=10" in req.full_url
