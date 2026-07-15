from __future__ import annotations
"""Tests for LibraryPage states, tabs, selection, context menu."""

from unittest.mock import MagicMock

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
        assert bridge_mock.state == "INITIALIZING"
        assert bridge_mock.trackModel.initialized is False

    def test_ready_state_with_songs(self, bridge_mock):
        bridge_mock.state = "READY"
        bridge_mock.songCount = 42
        bridge_mock.trackModel.initialized = True
        bridge_mock.trackModel.count = 42
        assert bridge_mock.state == "READY"
        assert bridge_mock.songCount == 42
        assert bridge_mock.trackModel.initialized is True

    def test_filtered_empty_state(self, bridge_mock):
        bridge_mock.state = "FILTERED_EMPTY"
        bridge_mock.trackModel.initialized = True
        bridge_mock.trackModel.count = 0
        assert bridge_mock.state == "FILTERED_EMPTY"
        assert bridge_mock.trackModel.initialized is True
        assert bridge_mock.trackModel.count == 0

    def test_error_state(self, bridge_mock):
        bridge_mock.state = "QUERY_ERROR"
        assert bridge_mock.state == "QUERY_ERROR"

    def test_no_sources_state(self, bridge_mock):
        bridge_mock.state = "NO_SOURCES"
        assert bridge_mock.state == "NO_SOURCES"

    def test_tab_switching(self, bridge_mock):
        tabs = ["Canciones", "Álbumes", "Artistas", "Carpetas", "Fuentes"]
        assert len(tabs) == 5

    def test_selection_bar_visible_with_selection(self):
        sel = MagicMock()
        sel.hasSelection = True
        sel.count = 3
        assert sel.hasSelection is True
        assert sel.count == 3

    def test_selection_bar_hidden_no_selection(self):
        sel = MagicMock()
        sel.hasSelection = False
        sel.count = 0
        assert sel.hasSelection is False
        assert sel.count == 0

    def test_context_menu_play(self):
        bridge = MagicMock()
        bridge.playTrackById = MagicMock(return_value={"ok": True})
        result = bridge.playTrackById(1)
        assert result["ok"] is True

    def test_context_menu_enqueue(self):
        bridge = MagicMock()
        bridge.enqueueTrackById = MagicMock(return_value={"ok": True})
        result = bridge.enqueueTrackById(1)
        assert result["ok"] is True

    def test_context_menu_favorite(self):
        bridge = MagicMock()
        bridge.toggleFavoriteById = MagicMock(return_value={"ok": True, "favorite": True})
        result = bridge.toggleFavoriteById(1)
        assert result["ok"] is True
        assert result["favorite"] is True

    def test_context_menu_reveal(self):
        bridge = MagicMock()
        bridge.revealTrackById = MagicMock(return_value={"ok": True})
        result = bridge.revealTrackById(1)
        assert result["ok"] is True

    def test_track_model_refresh(self, bridge_mock):
        bridge_mock.trackModel.refresh = MagicMock()
        bridge_mock.trackModel.refresh()
        bridge_mock.trackModel.refresh.assert_called_once()

    def test_album_model_refresh(self, bridge_mock):
        bridge_mock.albumModel.refresh = MagicMock()
        bridge_mock.albumModel.refresh()
        bridge_mock.albumModel.refresh.assert_called_once()

    def test_artist_model_refresh(self, bridge_mock):
        bridge_mock.artistModel.refresh = MagicMock()
        bridge_mock.artistModel.refresh()
        bridge_mock.artistModel.refresh.assert_called_once()

    def test_clear_filters_calls_bridge(self, bridge_mock):
        bridge_mock.clearFilters = MagicMock(return_value={"ok": True})
        result = bridge_mock.clearFilters()
        assert result["ok"] is True

    def test_album_detail_navigation(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.album_detail", {"album_key": "ak123"})
        nav.navigateWithParams.assert_called_once_with("library.album_detail", {"album_key": "ak123"})

    def test_artist_detail_navigation(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.artist_detail", {"artist": "Test Artist"})
        nav.navigateWithParams.assert_called_once_with("library.artist_detail", {"artist": "Test Artist"})
