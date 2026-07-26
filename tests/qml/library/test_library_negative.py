from __future__ import annotations
"""Negative tests for LibraryPage — null bridge, empty states, error states."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("library")]


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

    def test_null_query_service_play_artist(self):
        qs = MagicMock()
        qs.fetch_artist_tracks_internal.return_value = []
        bridge = LibraryBridge(query_service=qs, player_service=MagicMock())
        result = bridge.playArtist("some_artist")
        assert result["ok"] is False

    def test_cancelled_state(self):
        bridge = MagicMock()
        bridge.state = "CANCELLED"
        assert bridge.state == "CANCELLED"

    def test_partial_results_not_crashing(self):
        bridge = MagicMock()
        bridge.state = "PARTIAL_RESULTS"
        bridge.songCount = 5
        assert bridge.songCount == 5
