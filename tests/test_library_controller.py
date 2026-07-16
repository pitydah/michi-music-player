"""Tests for LibraryController — load, refresh, filter, tab management."""
from unittest.mock import MagicMock, patch

import pytest

from legacy_widgets.ui.controllers.legacy_controllers.library_controller import LibraryController


@pytest.fixture
def win():
    w = MagicMock()
    w._safe_mode = False
    w._workers = MagicMock()
    w._db = MagicMock()
    w._all_items = []
    w._items_index = {}
    w._search_ctrl = MagicMock()
    w._search_text = ""
    w._song_grid = MagicMock()
    w._album_grid = MagicMock()
    w._artist_repo = MagicMock()
    w._artist_grid = MagicMock()
    w._genre_repo = MagicMock()
    w._genre_grid = MagicMock()
    w._coverflow_cache_key = None
    w._current_section_key = ""
    w._view_mode = ""
    w._songs_stack = MagicMock()
    w._albums_stack = MagicMock()
    w._playlist_ctrl = MagicMock()
    w._show_song_grid = MagicMock()
    w._show_album_list = MagicMock()
    w._show_coverflow = MagicMock()
    w._show_album_grid = MagicMock()
    w._artists_stack = MagicMock()
    w._genres_stack = MagicMock()
    return w


@pytest.fixture
def ctrl(win):
    from PySide6.QtCore import QObject
    ctrl = LibraryController.__new__(LibraryController)
    QObject.__init__(ctrl)
    ctrl._win = win
    return ctrl


class TestLibraryController:
    def test_load_triggers_reload(self, ctrl, win):
        with patch.object(ctrl, 'reload_after_change') as mock_reload:
            ctrl.load()
            mock_reload.assert_called_with(reason="load")

    def test_load_schedules_backfill_tasks(self, ctrl, win):
        with patch.object(ctrl, 'reload_after_change'), \
             patch("core.settings_manager.get_bool", return_value=True):
            ctrl.load()
            win._workers.run_task.assert_any_call("backfill_meta",
                win._db.backfill_missing_metadata, on_done=ctrl._on_backfill_done)
            win._workers.run_task.assert_any_call("backfill_art",
                win._db.backfill_missing_album_art)

    def test_reload_after_change_loads_all_items(self, ctrl, win):
        item = MagicMock()
        item.filepath = "/path/item.flac"
        win._db.get_all.return_value = [item]
        ctrl.reload_after_change(reason="test")
        assert len(win._all_items) == 1
        win._rebuild_sidebar.assert_called_once()

    def test_reload_after_change_refreshes_tabs(self, ctrl, win):
        with patch.object(ctrl, 'refresh_all_tabs') as mock_all, \
             patch.object(ctrl, 'refresh_active_tab') as mock_active:
            ctrl.reload_after_change(reason="test")
            mock_all.assert_called_with(force=True)
            mock_active.assert_called_with(force=True)

    def test_apply_filters_calls_search(self, ctrl, win):
        win._search_text = "rock"
        ctrl.apply_filters()
        win._search_ctrl.search.assert_called_with("rock")

    def test_refresh_library_delegates(self, ctrl, win):
        ctrl.refresh_library()
        win._playlist_ctrl.refresh_library.assert_called_once()

    def test_refresh_all_tabs_calls_sub_refreshes(self, ctrl, win):
        win._all_items = [MagicMock()]
        with patch.object(ctrl, 'refresh_songs') as mock_s, \
             patch.object(ctrl, 'refresh_albums') as mock_a, \
             patch.object(ctrl, 'refresh_artists') as mock_ar, \
             patch.object(ctrl, 'refresh_genres') as mock_g:
            ctrl.refresh_all_tabs()
            mock_s.assert_called_once()
            mock_a.assert_called_once()
            mock_ar.assert_called_once()
            mock_g.assert_called_once()

    def test_refresh_all_tabs_loads_if_empty(self, ctrl, win):
        win._db.get_all.return_value = [MagicMock()]
        ctrl.refresh_all_tabs()
        assert len(win._all_items) > 0

    def test_refresh_all_tabs_returns_if_still_empty(self, ctrl, win):
        win._db.get_all.return_value = []
        ctrl.refresh_all_tabs()

    def test_refresh_songs_calls_set_items(self, ctrl, win):
        items = [MagicMock(), MagicMock()]
        win._all_items = items
        ctrl.refresh_songs()
        win._song_grid.set_items.assert_called_with(items, card_size=170)

    def test_refresh_albums_sets_cache_key_to_none(self, ctrl, win):
        win._all_items = [MagicMock()]
        ctrl.refresh_albums()
        assert win._coverflow_cache_key is None

    def test_refresh_albums_calls_set_items(self, ctrl, win):
        win._all_items = [MagicMock()]
        win._album_sort_key = "title"
        win._album_filter_mode = "all"
        ctrl.refresh_albums()
        win._album_grid.set_items.assert_called_once()

    def test_refresh_artists_builds_repo(self, ctrl, win):
        win._all_items = [MagicMock()]
        ctrl.refresh_artists()
        win._artist_repo.build.assert_called_with(win._all_items)

    def test_refresh_genres_builds_repo(self, ctrl, win):
        win._all_items = [MagicMock()]
        ctrl.refresh_genres()
        win._genre_repo.build.assert_called_with(win._all_items)

    def test_filtered_album_items_filters_by_search(self, ctrl, win):
        item_a = MagicMock()
        item_a.album = "Greatest Hits"
        item_a.artist = "Rock Band"
        item_a.albumartist = ""
        item_a.genre = "Rock"
        item_a.title = "Best Song"
        item_a.year = 2024
        item_a.kind = "audio"
        item_b = MagicMock()
        item_b.album = "Jazz Collection"
        item_b.artist = "Jazz Cat"
        item_b.albumartist = ""
        item_b.genre = "Jazz"
        item_b.title = "Cool Tune"
        item_b.year = 2023
        item_b.kind = "audio"
        win._all_items = [item_a, item_b]
        win._search_text = "rock"
        result = ctrl.filtered_album_items()
        assert len(result) == 1
        assert result[0].artist == "Rock Band"

    def test_filtered_album_items_returns_all_without_search(self, ctrl, win):
        win._all_items = [MagicMock(), MagicMock()]
        win._all_items[0].kind = "audio"
        win._all_items[1].kind = "audio"
        result = ctrl.filtered_album_items()
        assert len(result) == 2

    def test_filtered_album_items_skips_non_audio(self, ctrl, win):
        audio = MagicMock()
        audio.kind = "audio"
        non_audio = MagicMock()
        non_audio.kind = "video"
        win._all_items = [audio, non_audio]
        result = ctrl.filtered_album_items()
        assert len(result) == 1

    def test_refresh_active_tab_library_grid(self, ctrl, win):
        win._current_section_key = "library"
        win._view_mode = "grid"
        ctrl.refresh_active_tab()
        win._songs_stack.setCurrentIndex.assert_called_with(1)

    def test_refresh_active_tab_library_list(self, ctrl, win):
        win._current_section_key = "library"
        win._view_mode = "list"
        ctrl.refresh_active_tab()
        win._songs_stack.setCurrentIndex.assert_called_with(0)

    def test_refresh_active_tab_albums_list(self, ctrl, win):
        win._current_section_key = "albums"
        win._view_mode = "list"
        ctrl.refresh_active_tab()
        win._albums_stack.setCurrentIndex.assert_called_with(1)
        win._show_album_list.assert_called_once()

    def test_refresh_active_tab_albums_coverflow(self, ctrl, win):
        win._current_section_key = "albums"
        win._view_mode = "coverflow"
        ctrl.refresh_active_tab()
        win._show_coverflow.assert_called_once()

    def test_refresh_active_tab_albums_grid(self, ctrl, win):
        win._current_section_key = "albums"
        win._view_mode = "grid"
        ctrl.refresh_active_tab()
        win._albums_stack.setCurrentIndex.assert_called_with(0)
        win._show_album_grid.assert_called_once()

    def test_refresh_active_tab_artists(self, ctrl, win):
        win._current_section_key = "artists"
        with patch.object(ctrl, 'refresh_artists') as mock_ar:
            ctrl.refresh_active_tab()
            mock_ar.assert_called_once()

    def test_refresh_active_tab_genres(self, ctrl, win):
        win._current_section_key = "genres"
        with patch.object(ctrl, 'refresh_genres') as mock_g:
            ctrl.refresh_active_tab()
            mock_g.assert_called_once()

    def test_on_backfill_done_with_count(self, ctrl, win):
        with patch.object(ctrl, 'reload_after_change') as mock_reload:
            ctrl._on_backfill_done(5)
            mock_reload.assert_called_with(reason="backfill")

    def test_on_backfill_done_with_zero_count(self, ctrl, win):
        ctrl._on_backfill_done(0)
        # no reload should happen
