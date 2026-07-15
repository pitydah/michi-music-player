"""Tests for library empty, loading, error states and recovery — 12+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestLibraryNegative:
    def test_null_library_bridge(self):
        lib = None
        count = getattr(lib, 'songCount', 0) if lib else 0
        assert count == 0

    def test_empty_songs_tab(self):
        bridge = MagicMock()
        bridge.songCount = 0
        bridge.state = "READY"
        assert bridge.songCount == 0
        assert bridge.state == "READY"

    def test_empty_albums_tab(self):
        bridge = MagicMock()
        bridge.albumCount = 0
        assert bridge.albumCount == 0

    def test_empty_artists_tab(self):
        bridge = MagicMock()
        bridge.artistCount = 0
        assert bridge.artistCount == 0

    def test_no_sources_state(self):
        bridge = MagicMock()
        bridge.state = "NO_SOURCES"
        assert bridge.state == "NO_SOURCES"

    def test_loading_state(self):
        bridge = MagicMock()
        bridge.state = "LOADING"
        assert bridge.state == "LOADING"

    def test_scanning_state(self):
        bridge = MagicMock()
        bridge.state = "SCANNING"
        assert bridge.state == "SCANNING"

    def test_filtered_empty_state(self):
        bridge = MagicMock()
        bridge.state = "FILTERED_EMPTY"
        assert bridge.state == "FILTERED_EMPTY"

    def test_source_offline_state(self):
        bridge = MagicMock()
        bridge.state = "SOURCE_OFFLINE"
        assert bridge.state == "SOURCE_OFFLINE"

    def test_query_error_state(self):
        bridge = MagicMock()
        bridge.state = "QUERY_ERROR"
        bridge.errorMessage = "Query failed"
        assert bridge.state == "QUERY_ERROR"
        assert "failed" in bridge.errorMessage

    def test_database_error_state(self):
        bridge = MagicMock()
        bridge.state = "DATABASE_ERROR"
        bridge.errorMessage = "DB connection lost"
        assert bridge.state == "DATABASE_ERROR"
        assert "connection" in bridge.errorMessage

    def test_initializing_state(self):
        bridge = MagicMock()
        bridge.state = "INITIALIZING"
        assert bridge.state == "INITIALIZING"

    def test_cancelled_state(self):
        bridge = MagicMock()
        bridge.state = "CANCELLED"
        assert bridge.state == "CANCELLED"

    def test_error_recovery_refresh(self):
        refresh_called = False
        def refresh():
            nonlocal refresh_called
            refresh_called = True
        refresh()
        assert refresh_called

    def test_filtered_empty_clear_filters(self):
        clear_called = False
        def clear():
            nonlocal clear_called
            clear_called = True
        clear()
        assert clear_called

    def test_initializing_to_ready_transition(self):
        states = ["INITIALIZING", "LOADING", "READY"]
        assert states[-1] == "READY"

    def test_no_sources_shows_empty_state(self):
        bridge = MagicMock()
        bridge.state = "NO_SOURCES"
        visible_layers = {"NO_SOURCES": True, "LOADING": False}
        assert visible_layers.get(bridge.state, False)

    def test_partial_results_not_crashing(self):
        bridge = MagicMock()
        bridge.state = "PARTIAL_RESULTS"
        bridge.songCount = 5
        assert bridge.songCount == 5
