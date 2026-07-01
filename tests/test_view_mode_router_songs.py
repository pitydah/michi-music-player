"""Tests: ViewModeRouter — songs library list/grid with and without premium."""

from unittest.mock import MagicMock


class TestViewModeRouterSongs:

    def test_library_list_uses_premium_when_available(self):
        from ui.routers.view_mode_router import ViewModeRouter
        win = MagicMock()
        win._songs_ctrl = MagicMock()
        win._songs_premium_page = MagicMock()
        win._current_route_key = "library"
        win._current_section_key = "library"
        win._view_mode = "grid"
        win._songs_stack = MagicMock()
        win._apply_filters = MagicMock()
        win._fade_content = MagicMock()

        router = ViewModeRouter(win)
        router._show_current_section_view("list")

        win._songs_stack.setCurrentIndex.assert_called_once_with(0)
        win._apply_filters.assert_not_called()
        win._songs_ctrl.apply_filter.assert_called_once()
        win._songs_premium_page.load_data.assert_called_once()

    def test_library_list_falls_back_when_no_premium(self):
        from ui.routers.view_mode_router import ViewModeRouter
        win = MagicMock()
        win._songs_ctrl = None
        win._songs_premium_page = None
        win._current_route_key = "library"
        win._current_section_key = "library"
        win._view_mode = "grid"
        win._songs_stack = MagicMock()
        win._apply_filters = MagicMock()
        win._show_song_grid = MagicMock()
        win._fade_content = MagicMock()

        router = ViewModeRouter(win)
        router._show_current_section_view("list")

        win._songs_stack.setCurrentIndex.assert_called_once_with(0)
        win._apply_filters.assert_called_once()

    def test_library_grid_uses_song_grid(self):
        from ui.routers.view_mode_router import ViewModeRouter
        win = MagicMock()
        win._songs_ctrl = MagicMock()
        win._songs_premium_page = MagicMock()
        win._current_route_key = "library"
        win._current_section_key = "library"
        win._view_mode = "grid"
        win._songs_stack = MagicMock()
        win._apply_filters = MagicMock()
        win._show_song_grid = MagicMock()
        win._fade_content = MagicMock()

        router = ViewModeRouter(win)
        router._show_current_section_view("grid")

        win._songs_stack.setCurrentIndex.assert_called_once_with(1)
        win._show_song_grid.assert_called_once()
        win._apply_filters.assert_not_called()
        win._songs_ctrl.apply_filter.assert_not_called()
