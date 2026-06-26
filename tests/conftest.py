"""Shared fixtures for controller tests."""
import sqlite3
from unittest.mock import MagicMock
import pytest
from ui.controllers.artist_repository import ArtistRepository


class MockAppContext:
    def __init__(self, mock_win):
        self.db = mock_win._db
        self.player = mock_win._player
        self.playback = mock_win._playback
        self.model = mock_win._model
        self.search_ctrl = mock_win._search_ctrl
        self.search = mock_win._search_ctrl
        self.window = mock_win
        self.toast = mock_win._toast_svc
        self.player_bar = mock_win._player_bar_ctrl
        self.bg_theme = mock_win._bg_theme
        self.mpris = mock_win._mpris_ctrl
        self.navigator = mock_win._nav
        self.tray = mock_win._tray_ctrl
        # Widget facades
        self.views = mock_win._views
        self.section_title = mock_win._section_title
        self.section_subtitle = mock_win._section_subtitle
        self.view_switcher = mock_win._view_switcher
        self.artist_grid = mock_win._artist_grid
        self.artist_detail = mock_win._artist_detail
        self.metadata_editor = mock_win._metadata_editor
        self.artist_repo = mock_win._artist_repo
        self.items_index = mock_win._items_index
        self.current_ref = mock_win._current_ref
        self.current_section_key = mock_win._current_section_key
        self.view_mode = mock_win._view_mode
        self.expanded = mock_win._expanded
        self.table = mock_win._table
        self.count = mock_win._count
        self.content = MagicMock()
        self.transmit_mgr = mock_win._transmit_mgr
        self.eq_dlg = mock_win._eq_dlg
        self.mini_player = MagicMock()
        # Delegation methods
        self.navigate_sidebar = MagicMock()
        self.load_library = MagicMock()
        self.rebuild_sidebar = MagicMock()
        self.notify_track = MagicMock()
        self.configure_header = MagicMock()
        self.fade_to = MagicMock()
        self.restore_opacity = MagicMock()
        self.set_window_title = MagicMock()
        self.play_file = MagicMock()
        self.show_album_grid = MagicMock()


class MockWindow:
    """Simulates MainWindow attributes needed by controllers."""

    def __init__(self):
        self._db = MagicMock()
        self._db._conn = sqlite3.connect(":memory:")
        self._playback = MagicMock()
        self._player = MagicMock()
        self._toast_svc = MagicMock()
        self._toast_svc.show = MagicMock()
        self._artist_repo = ArtistRepository()
        self._artist_grid = MagicMock()
        self._artist_detail = MagicMock()
        self._metadata_editor = MagicMock()
        self._section_title = MagicMock()
        self._section_subtitle = MagicMock()
        self._view_switcher = MagicMock()
        self._views = MagicMock()
        self._model = MagicMock()
        self._table = MagicMock()
        self._items_index = {}
        self._current_ref = None
        self._current_section_key = "library"
        self._mpris_ctrl = MagicMock()
        self._player_bar_ctrl = MagicMock()
        self._bg_theme = MagicMock()
        self._tray_ctrl = MagicMock()
        self._transmit_mgr = MagicMock()
        from audio.audio_chain import DacConfig
        self._dac = DacConfig()
        self._fade_content = MagicMock()
        self._configure_header_for_section = MagicMock()
        self._rebuild_sidebar = MagicMock()
        self._load_library = MagicMock()
        self._notify_track = MagicMock()
        self._on_sidebar_navigate = MagicMock()
        self._play_file = MagicMock()
        self._show_album_grid = MagicMock()
        self._expanded = None
        self._eq_dlg = None
        self._view_mode = "grid"
        self._search = MagicMock()
        self._nav = MagicMock()
        self.setWindowTitle = MagicMock()
        self._search_ctrl = MagicMock()
        self._count = MagicMock()
        self._content = MagicMock()
        self._mini_player = MagicMock()
        self._show_library_hub_page = MagicMock()
        self._library_hub_page = MagicMock()
        self._artists_stack = MagicMock()
        self._genres_stack = MagicMock()
        self._fade_content = MagicMock()
        self._ctx = MockAppContext(self)


@pytest.fixture
def mock_window():
    return MockWindow()
