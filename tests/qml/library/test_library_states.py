"""Tests for LibraryBridge state management — 8+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock


from ui_qml_bridge.library_bridge import LibraryBridge, LibraryState
import pytest
pytestmark = [pytest.mark.qml_module("library")]


def test_initial_state():
    bridge = LibraryBridge()
    assert bridge.state == "INITIALIZING"


def test_state_property():
    bridge = LibraryBridge()
    assert hasattr(bridge, 'state')
    assert isinstance(bridge.state, str)


def test_all_states_defined():
    expected = ["INITIALIZING", "NO_SOURCES", "SOURCE_EMPTY", "SOURCE_OFFLINE",
                "SOURCE_PERMISSION_ERROR", "SCANNING", "INDEXING", "LOADING",
                "READY", "FILTERED_EMPTY", "DATABASE_ERROR", "QUERY_ERROR",
                "PARTIAL_RESULTS", "CANCELLED", "MISSING_CONTENT"]
    for s in expected:
        assert LibraryState(s).value == s


def test_state_transitions():
    state = LibraryState.INITIALIZING
    assert state == LibraryState.INITIALIZING
    state = LibraryState.SCANNING
    assert state == LibraryState.SCANNING
    state = LibraryState.READY
    assert state == LibraryState.READY
    state = LibraryState.DATABASE_ERROR
    assert state == LibraryState.DATABASE_ERROR


def test_ready_state_counts():
    bridge = LibraryBridge()
    bridge._track_model = MagicMock()
    bridge._track_model.totalCount = 42
    bridge._album_model = MagicMock()
    bridge._album_model.totalCount = 10
    bridge._artist_model = MagicMock()
    bridge._artist_model.count = 5
    assert bridge.songCount == 42
    assert bridge.albumCount == 10
    assert bridge.artistCount == 5


def test_error_message_property():
    bridge = LibraryBridge()
    bridge._error_message = "DB connection failed"
    assert bridge.errorMessage == "DB connection failed"


def test_active_sort_properties():
    bridge = LibraryBridge()
    bridge._sort_key = "year"
    bridge._sort_asc = False
    assert bridge.activeSortKey == "year"
    assert bridge.activeSortAscending is False


def test_page_size_property():
    bridge = LibraryBridge()
    assert bridge.pageSize == 100
    bridge.setPageSize(50)
    assert bridge.pageSize == 50


def test_search_query_property():
    bridge = LibraryBridge()
    bridge._search_query = "test"
    assert bridge.searchQuery == "test"


def test_visible_count_delegates():
    bridge = LibraryBridge()
    bridge._track_model = MagicMock()
    bridge._track_model.totalCount = 77
    assert bridge.visibleCount == 77


def test_has_more_songs_delegates():
    bridge = LibraryBridge()
    bridge._track_model = MagicMock()
    bridge._track_model.hasMore = True
    assert bridge.hasMoreSongs is True


def test_favorite_filters():
    bridge = LibraryBridge()
    result = bridge.setFavoritesFilter()
    assert result["ok"] is True
    assert bridge._filter_favorites is True

    result = bridge.setUnplayedFilter()
    assert result["ok"] is True
    assert bridge._filter_unplayed is True
    assert bridge._filter_favorites is False

    result = bridge.setMissingFilter()
    assert result["ok"] is True
    assert bridge._filter_missing is True


def test_format_filter_readback():
    bridge = LibraryBridge()
    bridge._filter_format = "flac"
    assert bridge.activeFormatFilter == "flac"


def test_genre_filter_readback():
    bridge = LibraryBridge()
    bridge._filter_genre = "Rock"
    assert bridge.activeGenreFilter == "Rock"
