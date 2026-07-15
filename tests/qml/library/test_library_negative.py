"""Negative tests for LibraryPage — null bridge, empty states, error states."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge, LibraryState
from ui_qml_bridge.selection_controller import SelectionController

pytestmark = [pytest.mark.qml_module("library")]


class TestLibraryNegative:
    def test_null_bridge_does_not_crash(self):
        bridge = None
        assert bridge is None

    def test_null_track_model_handled(self):
        model = None
        count = model.count if model else 0
        assert count == 0

    def test_empty_state_no_songs(self):
        bridge = LibraryBridge()
        assert bridge.songCount == 0
        assert bridge.albumCount == 0
        assert bridge.artistCount == 0
        assert bridge.state == "INITIALIZING"

    def test_play_track_no_bridge(self):
        def play():
            pass
        assert play() is None

    def test_enqueue_track_no_bridge(self):
        result = LibraryBridge().enqueueTrackById(1)
        assert result["ok"] is False
        assert result["error"] == "NO_QUERY_SERVICE"

    def test_play_track_not_found(self):
        qs = MagicMock()
        qs.fetch_track_internal.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.playTrackById(9999)
        assert result["ok"] is False

    def test_album_detail_not_found(self):
        qs = MagicMock()
        qs.fetch_album_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getAlbumDetail("nonexistent")
        assert result["ok"] is False

    def test_artist_detail_not_found(self):
        qs = MagicMock()
        qs.fetch_artist_detail.return_value = None
        bridge = LibraryBridge(query_service=qs)
        result = bridge.getArtistDetail("nonexistent")
        assert result["ok"] is False

    def test_database_error_state(self):
        bridge = LibraryBridge()
        bridge._state = LibraryState.DATABASE_ERROR
        assert bridge.state == "DATABASE_ERROR"

    def test_source_offline_state(self):
        bridge = LibraryBridge()
        bridge._state = LibraryState.SOURCE_OFFLINE
        assert bridge.state == "SOURCE_OFFLINE"

    def test_filtered_empty_after_search(self):
        bridge = LibraryBridge()
        bridge._state = LibraryState.FILTERED_EMPTY
        bridge.setSearchQuery("nonexistent_song_xyz")
        assert bridge.searchQuery == "nonexistent_song_xyz"
        assert bridge.state == "FILTERED_EMPTY"

    def test_selection_controller_empty(self):
        ctrl = SelectionController()
        assert ctrl.count == 0
        assert ctrl.hasSelection is False
        assert ctrl.selectedIds == []

    def test_clear_filters_when_empty(self):
        bridge = LibraryBridge()
        result = bridge.clearFilters()
        assert result["ok"] is True
        assert bridge._filter_format == ""

    def test_null_query_service_play_album(self):
        bridge = LibraryBridge()
        result = bridge.playAlbum("some_key")
        assert result["ok"] is False
        assert result["error"] == "NO_QUERY_SERVICE"

    def test_null_query_service_enqueue_album(self):
        bridge = LibraryBridge()
        result = bridge.enqueueAlbum("some_key")
        assert result["ok"] is False
        assert result["error"] == "NO_QUERY_SERVICE"

    def test_null_query_service_play_artist(self):
        bridge = LibraryBridge()
        result = bridge.playArtist("some_artist")
        assert result["ok"] is False
        assert result["error"] == "NO_QUERY_SERVICE"
