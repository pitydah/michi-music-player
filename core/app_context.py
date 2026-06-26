"""AppContext — dependency injection container for Michi Music Player controllers."""
from __future__ import annotations


class AppContext:
    """Holds references to the central dependencies of the application.
    Passed to controllers so they don't need direct MainWindow references."""

    def __init__(self, window):
        self._win = window
        self._sealed = False

        # ── Core services (initialized in __init__ before AppContext) ──
        self.db = window._db
        self.player = window._player
        self.playback = window._playback
        self.model = window._model
        self.search_ctrl = window._search_ctrl
        self.search = window._search_ctrl  # backward compat alias
        self.window = window  # backward compat alias

        self._sealed = True

        # ── Extracted services (may not be initialized yet — use getattr) ──
        self.toast = getattr(window, '_toast_svc', None)
        # NOTE: `player_bar` holds a PlayerBarController (facade), NOT the NowPlayingBar widget.
        # The raw widget is at `window._player_bar`.
        self.player_bar = getattr(window, '_player_bar_ctrl', None)
        self.bg_theme = getattr(window, '_bg_theme', None)
        self.mpris = getattr(window, '_mpris_ctrl', None)
        self.navigator = getattr(window, '_nav', None)
        self.tray = getattr(window, '_tray_ctrl', None)

    # ── Facade properties — stable public API for controllers ──

    @property
    def playback(self):
        return self._win._playback

    @playback.setter
    def playback(self, value):
        if getattr(self, '_sealed', False):
            raise RuntimeError("AppContext.playback is read-only after init")
        object.__setattr__(self, '_playback', value)

    @property
    def db(self):
        return self._win._db

    @db.setter
    def db(self, value):
        if getattr(self, '_sealed', False):
            raise RuntimeError("AppContext.db is read-only after init")

    @property
    def model(self):
        return self._win._model

    @model.setter
    def model(self, value):
        if getattr(self, '_sealed', False):
            raise RuntimeError("AppContext.model is read-only after init")

    @property
    def player(self):
        return self._win._player

    @player.setter
    def player(self, value):
        if getattr(self, '_sealed', False):
            raise RuntimeError("AppContext.player is read-only after init")

    @property
    def views(self):
        return self._win._views

    @property
    def section_title(self):
        return self._win._section_title

    @property
    def section_subtitle(self):
        return self._win._section_subtitle

    @property
    def view_switcher(self):
        return self._win._view_switcher

    @property
    def artist_grid(self):
        return self._win._artist_grid

    @property
    def artist_detail(self):
        return self._win._artist_detail

    @property
    def metadata_editor(self):
        return self._win._metadata_editor

    @property
    def artist_repo(self):
        return self._win._artist_repo

    @property
    def genre_repo(self):
        return self._win._genre_repo

    @property
    def genre_grid(self):
        return self._win._genre_grid

    @property
    def genre_detail(self):
        return self._win._genre_detail

    @property
    def all_items(self):
        return self._win._all_items

    @property
    def items_index(self):
        return self._win._items_index

    @property
    def current_ref(self):
        return self._win._current_ref

    @current_ref.setter
    def current_ref(self, value):
        self._win._current_ref = value

    @property
    def current_section_key(self):
        return self._win._current_section_key

    @property
    def view_mode(self):
        return self._win._view_mode

    @property
    def expanded(self):
        return self._win._expanded

    @expanded.setter
    def expanded(self, value):
        self._win._expanded = value

    @property
    def table(self):
        return self._win._table

    @property
    def count(self):
        return self._win._count

    @property
    def content(self):
        return self._win._content

    @property
    def transmit_mgr(self):
        return self._win._transmit_mgr

    @property
    def eq_dlg(self):
        return getattr(self._win, '_eq_dlg', None)

    @eq_dlg.setter
    def eq_dlg(self, value):
        self._win._eq_dlg = value

    # ── Delegation methods (stable, non-widget-access) ──

    def fade_to(self, view_name: str):
        self._win._fade_content(view_name)

    def restore_opacity(self):
        self._win._restore_central_opacity()

    def configure_header(self, section_key: str):
        self._win._configure_header_for_section(section_key)

    def navigate_sidebar(self, key: str):
        self._win._on_sidebar_navigate(key)

    def rebuild_sidebar(self):
        self._win._rebuild_sidebar()

    def load_library(self):
        self._win._load_library()

    def notify_track(self, title: str, artist: str):
        self._win._notify_track(title, artist)

    def set_window_title(self, title: str):
        self._win.setWindowTitle(title)

    def play_file(self, fp: str):
        self._win._play_file(fp)

    def show_album_grid(self):
        self._win._show_album_grid()

    # ── Library hub coordination ──

    def show_library_hub(self):
        self._win._show_library_hub_page()

    def set_library_tab(self, section_key: str):
        """Switch library hub tab: library/albums/artists/genres/folders."""
        if self._win._library_hub_page:
            self._win._library_hub_page.set_current_section(section_key)

    def set_artist_stack(self, index: int):
        if hasattr(self._win, '_artists_stack'):
            self._win._artists_stack.setCurrentIndex(index)

    def set_genre_stack(self, index: int):
        if hasattr(self._win, '_genres_stack'):
            self._win._genres_stack.setCurrentIndex(index)

    def play_filepaths(self, filepaths: list[str], play_now: bool = True):
        self._win._play_filepaths(filepaths, play_now=play_now)
