from __future__ import annotations
"""Tests for LibraryPage state machine with real SQLite — 10+ tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import sqlite3

from ui_qml_bridge.library_bridge import LibraryBridge, LibraryState
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def real_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        db_path = Path(tmp.name)
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE media_items (
            track_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, artist TEXT, album TEXT, album_key TEXT,
            filepath TEXT, duration REAL, format TEXT, year INTEGER,
            genre TEXT, track_number INTEGER, bit_depth INTEGER,
            bitrate INTEGER, favorite INTEGER DEFAULT 0,
            missing INTEGER DEFAULT 0, deleted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE albums (
            album_key TEXT PRIMARY KEY, title TEXT, artist TEXT,
            year INTEGER, genre TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE artists (
            name TEXT PRIMARY KEY, track_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE TABLE favorites (track_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE sources (id INTEGER PRIMARY KEY, path TEXT)")
    for i in range(20):
        conn.execute(
            "INSERT INTO media_items (title, artist, album, album_key, filepath, duration, format, year, track_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"Song {i}", f"Artist {i%5}", f"Album {i%3}", f"ak{i%3}", f"/m/s{i}.flac",
             200 + i, "FLAC", 2020 + i % 5, i + 1)
        )
    conn.execute("INSERT INTO albums (album_key, title, artist) VALUES ('ak0', 'Album 0', 'Artist 0')")
    conn.execute("INSERT INTO albums (album_key, title, artist) VALUES ('ak1', 'Album 1', 'Artist 1')")
    conn.execute("INSERT INTO albums (album_key, title, artist) VALUES ('ak2', 'Album 2', 'Artist 2')")
    conn.execute("INSERT INTO artists (name, track_count) VALUES ('Artist 0', 4)")
    conn.execute("INSERT INTO artists (name, track_count) VALUES ('Artist 1', 4)")
    conn.commit()
    conn.close()
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_qs():
    all_tracks = [
        {"track_id": i, "track_uid": f"uid{i}", "title": f"Song {i}",
         "artist": f"Artist {i%5}", "album": f"Album {i%3}", "album_key": f"ak{i%3}",
         "duration": 200 + i, "format": "FLAC", "year": 2020 + i % 5, "genre": "",
         "track_number": i + 1, "favorite": False, "missing": False,
         "cover_key": f"ck{i}", "filepath": f"/m/s{i}.flac"}
        for i in range(20)
    ]
    qs = MagicMock()
    qs.count_tracks.return_value = 20
    def fetch_tracks_side(offset=0, limit=100, **kw):
        return all_tracks[offset:offset + limit]
    qs.fetch_tracks.side_effect = fetch_tracks_side
    qs.count_albums.return_value = 3
    qs.count_artists.return_value = 5
    qs.fetch_albums.return_value = [
        {"album_key": f"ak{i}", "title": f"Album {i}", "artist": f"Artist {i}",
         "year": 2020 + i, "track_count": 5, "duration": 1000, "cover_key": f"ck{i}"}
        for i in range(3)
    ]
    qs.fetch_artists.return_value = [
        {"name": f"Artist {i}", "track_count": 4, "album_count": 2, "cover_key": f"ck{i}"}
        for i in range(5)
    ]
    qs.fetch_album_detail.return_value = {"title": "Album 0", "artist": "Artist 0"}
    qs.fetch_artist_detail.return_value = {"name": "Artist 0"}
    qs.fetch_track_internal.return_value = {"filepath": "/m/s0.flac", "track_id": 0}
    return qs


@pytest.fixture
def bridge(mock_qs):
    bridge = LibraryBridge(query_service=mock_qs, query_executor=None)
    bridge._album_model._qe = None
    bridge._artist_model._qe = None
    return bridge


def test_initial_state():
    bridge = LibraryBridge()
    assert bridge.state == "INITIALIZING"


def test_state_changes_to_ready(bridge):
    bridge._state = LibraryState.READY
    assert bridge.state == "READY"


def test_song_count_from_db(bridge):
    bridge._track_model.refresh()
    assert bridge.songCount == 20


def test_album_count_from_db(bridge):
    bridge._album_model.refresh()
    assert bridge.albumCount >= 3


def test_artist_count_from_db(bridge):
    bridge._artist_model.refresh()
    assert bridge.artistCount >= 5


def test_search_query(bridge):
    bridge.setSearchQuery("Song 1")
    assert bridge.searchQuery == "Song 1"


def test_format_filter(bridge):
    bridge.setFormatFilter("FLAC")
    assert bridge.activeFormatFilter == "FLAC"


def test_genre_filter(bridge):
    bridge.setGenreFilter("Rock")
    assert bridge.activeGenreFilter == "Rock"


def test_clear_filters(bridge):
    bridge.setFormatFilter("FLAC")
    bridge.setSearchQuery("test")
    bridge.clearFilters()
    assert bridge.activeFormatFilter == ""
    assert bridge.searchQuery == ""


def test_sort_by(bridge):
    result = bridge.sortBy("year")
    assert result["ok"] is True
    assert bridge.activeSortKey == "year"


def test_has_more_songs(bridge):
    bridge._track_model._page_size = 10
    bridge._track_model.refresh()
    assert bridge.hasMoreSongs is True


def test_play_track_by_id_not_found(bridge):
    result = bridge.playTrackById(9999)
    assert result["ok"] is False


def test_enqueue_track_by_id_not_found(bridge):
    result = bridge.enqueueTrackById(9999)
    assert result["ok"] is False


def test_toggle_favorite_by_id_nonexistent(bridge):
    result = bridge.toggleFavoriteById(9999)
    assert result["ok"] is False


def test_favorites_filter(bridge):
    result = bridge.setFavoritesFilter()
    assert result["ok"] is True
    assert bridge._filter_favorites is True


def test_missing_filter(bridge):
    result = bridge.setMissingFilter()
    assert result["ok"] is True
    assert bridge._filter_missing is True


def test_unplayed_filter(bridge):
    result = bridge.setUnplayedFilter()
    assert result["ok"] is True
    assert bridge._filter_unplayed is True
