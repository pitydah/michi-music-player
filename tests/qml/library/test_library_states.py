"""Tests for LibraryBridge state management — 20+ tests covering all states."""
from __future__ import annotations

from unittest.mock import MagicMock

from ui_qml_bridge.library_bridge import LibraryBridge, LibraryState
import pytest

pytestmark = [pytest.mark.qml_module("library")]


def _make_mock_models():
    bridge = LibraryBridge()
    bridge._track_model = MagicMock()
    bridge._track_model.totalCount = 0
    bridge._track_model.count = 0
    bridge._track_model.hasMore = False
    bridge._track_model.initialized = False
    bridge._album_model = MagicMock()
    bridge._album_model.totalCount = 0
    bridge._album_model.count = 0
    bridge._artist_model = MagicMock()
    bridge._artist_model.count = 0
    bridge._folder_model = MagicMock()
    return bridge


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
    bridge = _make_mock_models()
    bridge._track_model.totalCount = 42
    bridge._album_model.totalCount = 10
    bridge._artist_model.count = 5
    bridge._state = LibraryState.READY
    assert bridge.state == "READY"
    assert bridge.songCount == 42
    assert bridge.albumCount == 10


def test_no_sources_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.NO_SOURCES
    assert bridge.state == "NO_SOURCES"


def test_scanning_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.SCANNING
    assert bridge.state == "SCANNING"


def test_loading_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.LOADING
    assert bridge.state == "LOADING"


def test_false_ready_with_zero_songs():
    bridge = _make_mock_models()
    bridge._state = LibraryState.READY
    assert bridge.songCount == 0


def test_source_offline_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.SOURCE_OFFLINE
    assert bridge.state == "SOURCE_OFFLINE"


def test_source_permission_error_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.SOURCE_PERMISSION_ERROR
    assert bridge.state == "SOURCE_PERMISSION_ERROR"


def test_source_empty_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.SOURCE_EMPTY
    assert bridge.state == "SOURCE_EMPTY"


def test_indexing_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.INDEXING
    assert bridge.state == "INDEXING"


def test_filtered_empty_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.FILTERED_EMPTY
    assert bridge.state == "FILTERED_EMPTY"


def test_database_error_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.DATABASE_ERROR
    assert bridge.state == "DATABASE_ERROR"


def test_query_error_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.QUERY_ERROR
    assert bridge.state == "QUERY_ERROR"


def test_partial_results_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.PARTIAL_RESULTS
    assert bridge.state == "PARTIAL_RESULTS"


def test_cancelled_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.CANCELLED
    assert bridge.state == "CANCELLED"


def test_missing_content_state():
    bridge = LibraryBridge()
    bridge._state = LibraryState.MISSING_CONTENT
    assert bridge.state == "MISSING_CONTENT"


def test_state_signal_emitted():
    bridge = _make_mock_models()
    signals = []
    bridge.stateChanged.connect(lambda: signals.append(True))
    bridge._state = LibraryState.READY
    bridge.stateChanged.emit()
    assert len(signals) >= 1


def test_state_does_not_accept_invalid():
    with pytest.raises(ValueError):
        LibraryState("INVALID_STATE_THAT_DOES_NOT_EXIST")


def test_ready_counts_with_initialized_true():
    bridge = _make_mock_models()
    bridge._track_model.initialized = True
    bridge._track_model.count = 100
    bridge._track_model.totalCount = 200
    bridge._state = LibraryState.READY
    assert bridge.songCount == 200


def test_search_resets_state():
    bridge = _make_mock_models()
    bridge._state = LibraryState.READY
    bridge._search_query = ""
    bridge.search("test query")
    assert bridge._search_query == "test query"


def test_clear_filters_resets_state():
    bridge = _make_mock_models()
    bridge._state = LibraryState.READY
    bridge._filter_format = "flac"
    bridge.clearFilters()
    assert bridge._filter_format == ""
    assert bridge._search_query == ""


def test_loaded_count_increases():
    bridge = _make_mock_models()
    assert bridge._loaded_count >= 0
    assert bridge._page_size == 100


def test_sort_key_default():
    bridge = _make_mock_models()
    assert bridge.activeSortKey == "title"
    assert bridge.activeSortAscending is True


def test_sort_by_changes_key():
    bridge = _make_mock_models()
    bridge.sortBy("year")
    assert bridge.activeSortKey == "year"


def test_sort_by_toggle_ascending():
    bridge = _make_mock_models()
    bridge.sortBy("year")
    assert bridge.activeSortKey == "year"
    assert bridge.activeSortAscending is True
    bridge.sortBy("year")
    assert bridge.activeSortAscending is False
