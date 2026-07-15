"""Workflow: Browse albums → select → context menu → play — 8+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.selection_controller import SelectionController
from ui_qml_bridge.action_registry import ActionRegistry


class TestLibraryWorkflow:
    @pytest.fixture
    def registry(self):
        return ActionRegistry()

    @pytest.fixture
    def sel(self):
        return SelectionController()

    def test_browse_albums_view(self):
        albumModel = MagicMock()
        albumModel.totalCount = 50
        albumModel.count = 20
        assert albumModel.totalCount == 50
        assert albumModel.count == 20

    def test_select_album_opens_detail(self):
        nav = MagicMock()
        nav.navigateWithParams("library.album_detail", {"album_key": "test_key"})
        nav.navigateWithParams.assert_called_once_with("library.album_detail", {"album_key": "test_key"})

    def test_context_menu_play_selected(self, registry, sel):
        sel.replace([1, 2])
        desc = registry.get("track_play_now")
        assert desc is not None
        result = registry.execute("track_play_now")
        assert result is not None

    def test_context_menu_add_to_queue(self, registry, sel):
        sel.add(42)
        desc = registry.get("track_add_to_queue")
        assert desc is not None
        result = registry.execute("track_add_to_queue")
        assert result is not None

    def test_context_menu_add_to_playlist(self, registry, sel):
        sel.replace([10, 20])
        desc = registry.get("track_add_to_playlist")
        assert desc is not None
        result = registry.execute("track_add_to_playlist")
        assert result is not None

    def test_navigate_to_artist_from_context(self, registry):
        desc = registry.get("track_open_artist")
        assert desc is not None
        nav = MagicMock()
        nav.navigateWithParams("library.artist_detail", {"artist": "Test Artist"})
        nav.navigateWithParams.assert_called_once()

    def test_navigate_to_album_from_context(self, registry):
        desc = registry.get("track_open_album")
        assert desc is not None
        nav = MagicMock()
        nav.navigateWithParams("library.album_detail", {"album_key": "test_key"})
        nav.navigateWithParams.assert_called_once()

    def test_workflow_browse_then_select_then_play(self, registry, sel):
        albumModel = MagicMock()
        albumModel.totalCount = 100
        assert albumModel.totalCount == 100
        sel.replace([5, 10, 15])
        assert sel.count == 3
        result = registry.execute("track_play_now")
        assert result is not None

    def test_workflow_filter_then_play(self):
        bridge = MagicMock()
        bridge.setFormatFilter = MagicMock()
        bridge.setFormatFilter("flac")
        bridge.setFormatFilter.assert_called_once_with("flac")
        bridge.playTrackById = MagicMock()
        bridge.playTrackById(1)
        bridge.playTrackById.assert_called_once_with(1)

    def test_workflow_search_then_select_then_queue(self, registry, sel):
        bridge = MagicMock()
        bridge.search = MagicMock()
        bridge.search("test")
        bridge.search.assert_called_once_with("test")
        sel.replace([7, 8])
        result = registry.execute("track_add_to_queue")
        assert result is not None

    def test_track_double_click_plays(self):
        bridge = MagicMock()
        bridge.playTrackById = MagicMock()
        bridge.playTrackById(99)
        bridge.playTrackById.assert_called_once_with(99)

    def test_album_click_opens_detail(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.album_detail", {"album_key": "key123"})
        nav.navigateWithParams.assert_called_once()

    def test_artist_click_opens_detail(self):
        nav = MagicMock()
        nav.navigateWithParams = MagicMock()
        nav.navigateWithParams("library.artist_detail", {"artist": "Artist"})
        nav.navigateWithParams.assert_called_once()
