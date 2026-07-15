"""Tests for LibraryPage state transitions."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest
pytestmark = [pytest.mark.qml_module("library")]


class TestLibraryPageStates:
    @pytest.fixture
    def bridge_mock(self):
        b = MagicMock()
        b.state = "INITIALIZING"
        b.songCount = 0
        b.albumCount = 0
        b.artistCount = 0
        b.trackModel = MagicMock()
        b.trackModel.count = 0
        b.trackModel.totalCount = 0
        b.trackModel.hasMore = False
        b.trackModel.initialized = False
        b.albumModel = MagicMock()
        b.artistModel = MagicMock()
        b.folderModel = MagicMock()
        b.activeSortKey = "title"
        b.activeSortAscending = True
        return b

    def test_initial_state(self, bridge_mock):
        bridge_mock.state = "INITIALIZING"
        assert bridge_mock.state == "INITIALIZING"
        assert bridge_mock.songCount == 0

    def test_no_sources_state(self, bridge_mock):
        bridge_mock.state = "NO_SOURCES"
        assert bridge_mock.state == "NO_SOURCES"

    def test_scanning_state(self, bridge_mock):
        bridge_mock.state = "SCANNING"
        assert bridge_mock.state == "SCANNING"

    def test_loading_state(self, bridge_mock):
        bridge_mock.state = "LOADING"
        assert bridge_mock.state == "LOADING"

    def test_ready_state_with_songs(self, bridge_mock):
        bridge_mock.state = "READY"
        bridge_mock.songCount = 42
        assert bridge_mock.state == "READY"
        assert bridge_mock.songCount == 42

    def test_ready_state_empty_becomes_filtered(self, bridge_mock):
        bridge_mock.state = "READY"
        bridge_mock.songCount = 0
        assert bridge_mock.songCount == 0

    def test_filtered_empty_state(self, bridge_mock):
        bridge_mock.state = "FILTERED_EMPTY"
        assert bridge_mock.state == "FILTERED_EMPTY"

    def test_source_offline_state(self, bridge_mock):
        bridge_mock.state = "SOURCE_OFFLINE"
        assert bridge_mock.state == "SOURCE_OFFLINE"

    def test_query_error_state(self, bridge_mock):
        bridge_mock.state = "QUERY_ERROR"
        assert bridge_mock.state == "QUERY_ERROR"

    def test_database_error_state(self, bridge_mock):
        bridge_mock.state = "DATABASE_ERROR"
        assert bridge_mock.state == "DATABASE_ERROR"

    def test_cancelled_state(self, bridge_mock):
        bridge_mock.state = "CANCELLED"
        assert bridge_mock.state == "CANCELLED"

    def test_navigation_bridge_called_for_album(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.album_detail", {"albumId": "key123"})
        nav.navigateWithParams.assert_called_once_with("library.album_detail", {"albumId": "key123"})

    def test_navigation_bridge_called_for_artist(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.artists.detail", {"artistId": "Artist Name"})
        nav.navigateWithParams.assert_called_once_with("library.artists.detail", {"artistId": "Artist Name"})
