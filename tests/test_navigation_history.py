"""Tests for navigation history — tabs, detail routes, shortcuts, no back buttons."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════
# NavigationHistory unit tests
# ═══════════════════════════════════════════════════════

class TestNavigationHistory:

    def test_push_and_back(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("home")
        h.push("library")
        h.push("albums")
        entry = h.back()
        assert entry is not None
        assert entry[0] == "library"
        assert h.current_key == "library"
        entry = h.back()
        assert entry is not None
        assert entry[0] == "home"

    def test_forward_restores(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("home")
        h.push("library")
        h.push("albums")
        h.back()
        h.back()
        entry = h.forward()
        assert entry is not None
        assert entry[0] == "library"
        entry = h.forward()
        assert entry is not None
        assert entry[0] == "albums"

    def test_no_forward_at_tip(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("home")
        h.push("albums")
        assert h.forward() is None

    def test_no_back_at_start(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("home")
        assert h.back() is None

    def test_force_push_creates_entry(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("albums")
        h.push("albums", force=True)
        assert h._index == 1
        assert h._history[1][0] == "albums"

    def test_tab_sequence(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("library")
        h.push("albums")
        h.push("artists")
        h.push("genres")
        assert h.back()[0] == "artists"
        assert h.back()[0] == "albums"
        assert h.back()[0] == "library"
        assert h.back() is None
        assert h.forward()[0] == "albums"
        assert h.forward()[0] == "artists"
        assert h.forward()[0] == "genres"

    def test_detail_route_back_forward(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("albums")
        h.push("album:k1", force=True)
        assert h.current_key == "album:k1"
        entry = h.back()
        assert entry[0] == "albums"
        entry = h.forward()
        assert entry[0] == "album:k1"

    def test_artist_detail_route_back_forward(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("artists")
        h.push("artist:k1", force=True)
        entry = h.back()
        assert entry[0] == "artists"
        entry = h.forward()
        assert entry[0] == "artist:k1"

    def test_genre_detail_route_back_forward(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        h.push("genres")
        h.push("genre:k1", force=True)
        entry = h.back()
        assert entry[0] == "genres"
        entry = h.forward()
        assert entry[0] == "genre:k1"

    def test_restoring_flag(self):
        from ui.controllers.navigation_controller import NavigationHistory
        h = NavigationHistory()
        assert h.is_restoring is False
        h._restoring = True
        assert h.is_restoring is True


# ═══════════════════════════════════════════════════════
# Resolve sidebar active key for detail routes
# ═══════════════════════════════════════════════════════

class TestResolveSidebarKey:

    def test_album_detail_maps_to_library_hub(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("album:k1") == "library_hub"

    def test_artist_detail_maps_to_library_hub(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("artist:k1") == "library_hub"

    def test_genre_detail_maps_to_library_hub(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("genre:k1") == "library_hub"


# ═══════════════════════════════════════════════════════
# Shortcuts exist in source code
# ═══════════════════════════════════════════════════════

class TestNavigationShortcuts:

    def test_alt_left_in_source(self):
        import inspect
        from legacy_widgets.ui.controllers.legacy_controllers.shortcut_controller import ShortcutController
        source = inspect.getsource(ShortcutController.setup)
        assert "Alt+Left" in source
        assert "navigate_back" in source

    def test_alt_right_in_source(self):
        import inspect
        from legacy_widgets.ui.controllers.legacy_controllers.shortcut_controller import ShortcutController
        source = inspect.getsource(ShortcutController.setup)
        assert "Alt+Right" in source
        assert "navigate_forward" in source

    def test_guard_for_missing_nav_ctrl(self):
        import inspect
        from legacy_widgets.ui.controllers.legacy_controllers.shortcut_controller import ShortcutController
        source = inspect.getsource(ShortcutController.setup)
        assert "nav_ctrl" in source or "_nav_ctrl" in source

    def test_focus_guard(self):
        import inspect
        from legacy_widgets.ui.controllers.legacy_controllers.shortcut_controller import ShortcutController
        source = inspect.getsource(ShortcutController.setup)
        assert "_focus_is_editable" in source

    def test_alt_left_not_in_editable(self):
        from ui.controllers.shortcut_controller import _focus_is_editable
        assert _focus_is_editable.__doc__ is not None
        assert "editable" in _focus_is_editable.__doc__.lower()


# ═══════════════════════════════════════════════════════
# Dispatch handles detail routes  (test NavigationController through logic only)
# ═══════════════════════════════════════════════════════

class TestDispatchDynamicRoutes:

    def test_dispatch_calls_show_album_detail_route(self):
        from ui.controllers.navigation_controller import NavigationController, NavigationHistory
        w = MagicMock()
        w._search_text = ""
        w._current_route_key = "albums"
        w._search = MagicMock()
        w._search.text.return_value = ""
        w._restore_central_opacity = MagicMock()
        w._context_svc = MagicMock()
        w._sidebar_controller = MagicMock()
        w._show_library_hub_page = MagicMock()
        w._library_hub_page = MagicMock()
        w._album_data_repo = MagicMock()
        w._album_ctrl = MagicMock()
        w._back_btn = MagicMock()
        w._forward_btn = MagicMock()
        w._show_album_detail_route = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._section_icon = MagicMock()
        w._view_switcher = MagicMock()
        w._album_sort_btn = MagicMock()
        w._album_filter_btn = MagicMock()
        w._view_mode = "grid"
        nav = NavigationController.__new__(NavigationController)
        nav._win = w
        nav._history = NavigationHistory()
        with patch.object(nav, 'configure_header'):
            nav.dispatch("album:k1")
        w._show_album_detail_route.assert_called_once_with("k1")

    def test_dispatch_calls_show_artist_detail_route(self):
        from ui.controllers.navigation_controller import NavigationController, NavigationHistory
        w = MagicMock()
        w._search_text = ""
        w._current_route_key = "artists"
        w._search = MagicMock()
        w._search.text.return_value = ""
        w._restore_central_opacity = MagicMock()
        w._context_svc = MagicMock()
        w._sidebar_controller = MagicMock()
        w._show_library_hub_page = MagicMock()
        w._library_hub_page = MagicMock()
        w._artist_ctrl = MagicMock()
        w._back_btn = MagicMock()
        w._forward_btn = MagicMock()
        w._show_artist_detail_route = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._section_icon = MagicMock()
        w._view_switcher = MagicMock()
        w._album_sort_btn = MagicMock()
        w._album_filter_btn = MagicMock()
        w._view_mode = "grid"
        nav = NavigationController.__new__(NavigationController)
        nav._win = w
        nav._history = NavigationHistory()
        with patch.object(nav, 'configure_header'):
            nav.dispatch("artist:k1")
        w._show_artist_detail_route.assert_called_once_with("k1")

    def test_dispatch_calls_show_genre_detail_route(self):
        from ui.controllers.navigation_controller import NavigationController, NavigationHistory
        w = MagicMock()
        w._search_text = ""
        w._current_route_key = "genres"
        w._search = MagicMock()
        w._search.text.return_value = ""
        w._restore_central_opacity = MagicMock()
        w._context_svc = MagicMock()
        w._sidebar_controller = MagicMock()
        w._show_library_hub_page = MagicMock()
        w._library_hub_page = MagicMock()
        w._genre_ctrl = MagicMock()
        w._back_btn = MagicMock()
        w._forward_btn = MagicMock()
        w._show_genre_detail_route = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._section_icon = MagicMock()
        w._view_switcher = MagicMock()
        w._album_sort_btn = MagicMock()
        w._album_filter_btn = MagicMock()
        w._view_mode = "grid"
        nav = NavigationController.__new__(NavigationController)
        nav._win = w
        nav._history = NavigationHistory()
        with patch.object(nav, 'configure_header'):
            nav.dispatch("genre:k1")
        w._show_genre_detail_route.assert_called_once_with("k1")


# ═══════════════════════════════════════════════════════
# No back buttons in detail views (introspect source)
# ═══════════════════════════════════════════════════════

class TestNoCentralBackButtons:

    def test_album_detail_has_no_back_button(self):
        import inspect
        from ui.album_detail_view import AlbumDetailView
        source = inspect.getsource(AlbumDetailView.__init__)
        assert "_back_btn" not in source
        assert "Volver" not in source and "Atrás" not in source

    def test_expanded_view_back_is_not_history(self):
        from ui.expanded_view import ExpandedNowPlaying
        assert not hasattr(ExpandedNowPlaying, 'navigate_back')
        assert not hasattr(ExpandedNowPlaying, 'history_back')
