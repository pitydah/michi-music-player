"""Tests for ArtistDetailPage and full artist workflow — 10+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge, LibraryState
pytestmark = [pytest.mark.qml_module("album_views")]



@pytest.fixture
def bridge():
    qs = MagicMock()
    qs.fetch_artist_detail.return_value = {
        "name": "Test Artist",
        "album_count": 5,
        "track_count": 42,
        "genre": "Rock",
    }
    return LibraryBridge(query_service=qs)


def test_bridge_artist_detail(bridge):
    result = bridge.getArtistDetail("Test Artist")
    assert result["ok"] is True
    assert result.get("name") == "Test Artist"
    assert result.get("album_count") == 5
    assert result.get("track_count") == 42


def test_bridge_artist_detail_not_found():
    qs = MagicMock()
    qs.fetch_artist_detail.return_value = None
    bridge = LibraryBridge(query_service=qs)
    result = bridge.getArtistDetail("Unknown")
    assert not result["ok"]
    assert result["error"] == "NOT_FOUND"


def test_bridge_artist_detail_no_qs():
    bridge = LibraryBridge()
    result = bridge.getArtistDetail("Test")
    assert not result["ok"]
    assert result["error"] == "NO_QUERY_SERVICE"


def test_bridge_play_artist(bridge):
    qs = bridge._query_svc
    qs.fetch_artist_tracks_internal.return_value = [
        {"filepath": "/music/song1.flac"},
        {"filepath": "/music/song2.flac"},
    ]
    pb = MagicMock()
    bridge._playback_ctrl = pb
    result = bridge.playArtist("Test Artist")
    assert result["ok"] is True
    assert result["count"] == 2


def test_bridge_play_artist_no_tracks(bridge):
    qs = bridge._query_svc
    qs.fetch_artist_tracks_internal.return_value = []
    result = bridge.playArtist("Test Artist")
    assert not result["ok"]


def test_bridge_play_artist_no_playback(bridge):
    result = bridge.playArtist("Test Artist")
    assert not result["ok"]


def test_bridge_get_artist_albums(bridge):
    qs = bridge._query_svc
    qs.fetch_artist_tracks_internal.return_value = [
        {"album_key": "k1"}, {"album_key": "k2"}, {"album_key": "k1"},
    ]
    albums = bridge.getArtistAlbums("Test")
    assert len(albums) == 2
    assert albums[0]["album_key"] == "k1"


def test_bridge_get_artist_tracks(bridge):
    qs = bridge._query_svc
    qs.fetch_artist_tracks_internal.return_value = [
        {"track_id": 1, "title": "Song A", "artist": "Test Artist"},
    ]
    tracks = bridge.getArtistTracks("Test Artist")
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Song A"


def test_bridge_artist_filter(bridge):
    result = bridge.filterByArtist("Test Artist")
    assert result["ok"] is True
    assert bridge._filter_artist == "Test Artist"


def test_library_state_enum():
    assert LibraryState.INITIALIZING.value == "INITIALIZING"
    assert LibraryState.READY.value == "READY"
    assert LibraryState.NO_SOURCES.value == "NO_SOURCES"
    assert LibraryState.FILTERED_EMPTY.value == "FILTERED_EMPTY"
    assert LibraryState.DATABASE_ERROR.value == "DATABASE_ERROR"
    assert LibraryState.SCANNING.value == "SCANNING"


def test_bridge_state_property(bridge):
    assert bridge.state == "INITIALIZING"


def test_bridge_initial_counts(bridge):
    assert bridge.songCount == 0
    assert bridge.albumCount == 0
    assert bridge.artistCount == 0


def test_bridge_clear_filters(bridge):
    bridge._filter_artist = "Test"
    bridge._filter_format = "flac"
    result = bridge.clearFilters()
    assert result["ok"] is True
    assert bridge._filter_artist == ""
    assert bridge._filter_format == ""
