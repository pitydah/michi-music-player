from __future__ import annotations
"""Tests for ArtistDetailPage — artist detail, albums, shuffle."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("album_views")]


class TestArtistDetail:
    @pytest.fixture
    def bridge(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = {
            "name": "Test Artist",
            "album_count": 5,
            "track_count": 42,
            "genre": "Rock",
            "aliases": "Testy",
            "is_album_artist": True,
            "bio": "A test artist bio",
        }
        qs.fetch_artist_tracks_internal.return_value = [
            {"track_id": 1, "title": "Song A", "artist": "Test Artist",
             "album": "Album 1", "album_key": "ak1",
             "duration": 200, "filepath": "/m/a.flac", "disc_number": 1,
             "track_number": 1, "format": "FLAC", "missing": False},
            {"track_id": 2, "title": "Song B", "artist": "Test Artist",
             "album": "Album 2", "album_key": "ak2",
             "duration": 180, "filepath": "/m/b.flac", "disc_number": 1,
             "track_number": 1, "format": "FLAC", "missing": False},
        ]
        return LibraryBridge(query_service=qs)

    def test_artist_detail_loads(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail["ok"] is True
        assert detail["name"] == "Test Artist"
        assert detail["album_count"] == 5
        assert detail["track_count"] == 42
        assert detail["genre"] == "Rock"

    def test_artist_aliases(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail["aliases"] == "Testy"

    def test_artist_is_album_artist(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail["is_album_artist"] is True

    def test_artist_bio(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        assert detail["bio"] == "A test artist bio"

    def test_artist_tracks(self, bridge):
        tracks = bridge.getArtistTracks("Test Artist")
        assert len(tracks) == 2
        assert tracks[0]["title"] == "Song A"

    def test_artist_albums(self, bridge):
        albums = bridge.getArtistAlbums("Test Artist")
        assert len(albums) == 2
        assert albums[0]["album_key"] == "ak1"

    def test_play_artist(self, bridge):
        pb = MagicMock()
        bridge._playback_ctrl = pb
        result = bridge.playArtist("Test Artist")
        assert result["ok"] is True
        assert result["count"] == 2

    def test_play_artist_no_tracks(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = {"name": "Empty Artist", "album_count": 0, "track_count": 0}
        qs.fetch_artist_tracks_internal.return_value = []
        bridge = LibraryBridge(query_service=qs)
        result = bridge.playArtist("Empty Artist")
        assert result["ok"] is False

    def test_play_artist_no_playback(self, bridge):
        result = bridge.playArtist("Test Artist")
        assert result["ok"] is False

    def test_artist_detail_not_found(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getArtistDetail("Unknown")
        assert result["ok"] is False

    def test_artist_detail_no_query_service(self):
        bridge = LibraryBridge()
        result = bridge.getArtistDetail("Test")
        assert result["ok"] is False

    def test_artist_album_count_deduplication(self, bridge):
        qs = bridge._query_svc
        qs.fetch_artist_tracks_internal.return_value = [
            {"album_key": "k1"}, {"album_key": "k2"}, {"album_key": "k1"},
            {"album_key": "k3"}, {"album_key": "k2"},
        ]
        albums = bridge.getArtistAlbums("Test")
        assert len(albums) == 3

    def test_artist_shuffle(self, bridge):
        pb = MagicMock()
        bridge._playback_ctrl = pb
        tracks = bridge.getArtistTracks("Test Artist")
        if tracks:
            bridge.playTrackById(tracks[0]["track_id"])

    def test_artist_enqueue(self, bridge):
        pb = MagicMock()
        bridge._playback_ctrl = pb
        result = bridge.playArtist("Test Artist")
        assert result["ok"] is True

    def test_artist_filter(self, bridge):
        result = bridge.filterByArtist("Test Artist")
        assert result["ok"] is True
        assert bridge._filter_artist == "Test Artist"

    def test_artist_track_count_summary(self, bridge):
        detail = bridge.getArtistDetail("Test Artist")
        tracks = bridge.getArtistTracks("Test Artist")
        assert detail["track_count"] >= len(tracks)
