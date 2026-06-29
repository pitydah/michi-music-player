"""Tests for AppContext — dependency container for controllers."""
from unittest.mock import MagicMock
from core.app_context import AppContext


class TestAppContext:
    def test_exposes_dependencies(self):
        w = MagicMock()
        w._db = "mock_db"
        w._player = "mock_player"
        w._playback = "mock_playback"
        w._model = "mock_model"
        w._search_ctrl = "mock_search"
        w._toast_svc = MagicMock()
        w._player_bar_ctrl = MagicMock()
        w._bg_theme = MagicMock()
        w._mpris_ctrl = MagicMock()
        w._nav = MagicMock()
        w._tray_ctrl = MagicMock()
        w._views = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._view_switcher = MagicMock()
        w._artist_grid = MagicMock()
        w._artist_detail = MagicMock()
        w._metadata_editor = MagicMock()
        w._artist_repo = MagicMock()
        w._items_index = {}
        w._current_ref = None
        w._current_section_key = "library"
        w._view_mode = "grid"
        w._expanded = None
        w._table = MagicMock()
        w._count = MagicMock()
        w._content = MagicMock()
        w._transmit_mgr = MagicMock()
        w._eq_dlg = None
        w._fade_content = MagicMock()
        w._restore_central_opacity = MagicMock()
        w._configure_header_for_section = MagicMock()
        w._on_sidebar_navigate = MagicMock()
        w._rebuild_sidebar = MagicMock()
        w._load_library = MagicMock()
        w._notify_track = MagicMock()
        w.setWindowTitle = MagicMock()
        w._play_file = MagicMock()
        w._show_album_grid = MagicMock()

        ctx = AppContext(w)

        assert ctx.db == "mock_db"
        assert ctx.player == "mock_player"
        assert ctx.playback == "mock_playback"
        assert ctx.model == "mock_model"
        assert ctx.search_ctrl == "mock_search"

    def test_window_reference(self):
        w = MagicMock()
        w._db = MagicMock()
        w._player = MagicMock()
        w._playback = MagicMock()
        w._model = MagicMock()
        w._search_ctrl = MagicMock()
        w._toast_svc = MagicMock()
        w._player_bar_ctrl = MagicMock()
        w._bg_theme = MagicMock()
        w._mpris_ctrl = MagicMock()
        w._nav = MagicMock()
        w._tray_ctrl = MagicMock()
        w._views = MagicMock()
        w._section_title = MagicMock()
        w._section_subtitle = MagicMock()
        w._view_switcher = MagicMock()
        w._artist_grid = MagicMock()
        w._artist_detail = MagicMock()
        w._metadata_editor = MagicMock()
        w._artist_repo = MagicMock()
        w._items_index = {}
        w._current_ref = None
        w._current_section_key = "library"
        w._view_mode = "grid"
        w._expanded = None
        w._table = MagicMock()
        w._count = MagicMock()
        w._content = MagicMock()
        w._transmit_mgr = MagicMock()
        w._eq_dlg = None
        w._fade_content = MagicMock()
        w._restore_central_opacity = MagicMock()
        w._configure_header_for_section = MagicMock()
        w._on_sidebar_navigate = MagicMock()
        w._rebuild_sidebar = MagicMock()
        w._load_library = MagicMock()
        w._notify_track = MagicMock()
        w.setWindowTitle = MagicMock()
        w._play_file = MagicMock()
        w._show_album_grid = MagicMock()

        ctx = AppContext(w)
        assert ctx.db is w._db
        assert ctx.player is w._player
        assert ctx.playback is w._playback
        assert ctx.model is w._model
        assert ctx.search_ctrl is w._search_ctrl
        assert ctx.toast is w._toast_svc
        assert ctx.player_bar is w._player_bar_ctrl
        assert ctx.views is w._views
        assert ctx.transmit_mgr is w._transmit_mgr

    def test_context_svc_property(self):
        w = MagicMock()
        w._context_svc = "mock_context"
        w._db = w._player = w._playback = w._model = w._search_ctrl = MagicMock()
        w._toast_svc = w._player_bar_ctrl = w._bg_theme = w._mpris_ctrl = MagicMock()
        w._nav = w._tray_ctrl = w._views = w._section_title = MagicMock()
        w._section_subtitle = w._view_switcher = w._artist_grid = MagicMock()
        w._artist_detail = w._metadata_editor = w._artist_repo = MagicMock()
        w._items_index = {}
        w._current_ref = None
        w._current_section_key = "library"
        w._view_mode = "grid"
        w._expanded = w._table = w._count = w._content = w._transmit_mgr = None
        w._eq_dlg = None
        w._fade_content = w._restore_central_opacity = MagicMock()
        w._configure_header_for_section = w._on_sidebar_navigate = MagicMock()
        w._rebuild_sidebar = w._load_library = w._notify_track = MagicMock()
        w.setWindowTitle = w._play_file = w._show_album_grid = MagicMock()

        ctx = AppContext(w)
        assert ctx.context_svc == "mock_context"
