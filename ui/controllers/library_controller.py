"""LibraryController — data loading, filtering, and tab refresh orchestration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.library_controller")


class LibraryController(QObject):
    """Owns the library data pipeline: load, filter, refresh all tabs."""

    def __init__(self, window: MainWindow):
        super().__init__(window)
        self._win = window

    # ── Public entry points ──

    def load(self):
        """Full library load with backfill tasks scheduled."""
        self.reload_after_change(reason="load")
        workers = self._win._workers
        if workers:
            workers.run_task("backfill_meta",
                self._win._db.backfill_missing_metadata,
                on_done=self._on_backfill_done)
            workers.run_task("backfill_art",
                self._win._db.backfill_missing_album_art)

    def reload_after_change(self, reason: str = ""):
        """Centralized data reload entry point for all mutations."""
        w = self._win
        w._all_items = w._db.get_all()
        w._items_index = {i.filepath: i for i in w._all_items}
        w._search_ctrl.set_active("local")
        w._rebuild_sidebar()
        self.refresh_all_tabs(force=True)
        self.refresh_active_tab(force=True)

    def apply_filters(self):
        self._win._search_ctrl.search(self._win._search_text)

    def refresh_library(self):
        self._win._playlist_ctrl.refresh_library()

    # ── Tab data refreshes ──

    def refresh_all_tabs(self, force: bool = False):
        w = self._win
        if not w._all_items and w._db:
            w._all_items = w._db.get_all()
            w._items_index = {i.filepath: i for i in w._all_items}
        if not w._all_items:
            return
        self.refresh_songs()
        self.refresh_albums()
        self.refresh_artists()
        self.refresh_genres()

    def refresh_songs(self):
        self._win._song_grid.set_items(self._win._all_items, card_size=170)

    def refresh_albums(self):
        w = self._win
        w._album_grid.set_items(self._album_items(), 200,
            sort_key=getattr(w, '_album_sort_key', 'title'),
            filter_mode=getattr(w, '_album_filter_mode', 'all'))
        w._coverflow_cache_key = None

    def refresh_artists(self):
        w = self._win
        if w._artist_repo:
            w._artist_repo.build(w._all_items)
            w._artist_grid.set_artists(w._artist_repo.groups)

    def refresh_genres(self):
        w = self._win
        if hasattr(w, '_genre_repo') and w._genre_repo:
            w._genre_repo.build(w._all_items)
            w._genre_grid.set_genres(w._genre_repo.groups, w._genre_repo.families)

    # ── Active tab state-aware refresh ──

    def refresh_active_tab(self, force: bool = False):
        w = self._win
        section = w._current_section_key
        if section == "library":
            if w._view_mode == "grid":
                w._songs_stack.setCurrentIndex(1)
                w._show_song_grid()
            else:
                w._songs_stack.setCurrentIndex(0)
                self.apply_filters()
        elif section == "albums":
            if w._view_mode == "list":
                w._albums_stack.setCurrentIndex(1)
                w._show_album_list()
            elif w._view_mode == "coverflow":
                w._show_coverflow()
            else:
                w._albums_stack.setCurrentIndex(0)
                w._show_album_grid()
        elif section == "artists":
            self.refresh_artists()
            if hasattr(w, '_artists_stack'):
                w._artists_stack.setCurrentIndex(0)
        elif section == "genres":
            self.refresh_genres()
            if hasattr(w, '_genres_stack'):
                w._genres_stack.setCurrentIndex(0)

    # ── Album helpers ──

    def _album_items(self) -> list:
        w = self._win
        if not w._all_items and w._db:
            w._all_items = w._db.get_all()
            w._items_index = {i.filepath: i for i in w._all_items}
        return [i for i in w._all_items if getattr(i, "kind", "audio") == "audio"]

    def filtered_album_items(self) -> list:
        items = self._album_items()
        q = (self._win._search_text or "").lower().strip()
        if not q:
            return items
        return [
            i for i in items
            if q in (getattr(i, "album", "") or "Sin álbum").lower()
            or q in (getattr(i, "artist", "") or "Artista desconocido").lower()
            or q in (getattr(i, "albumartist", "") or "").lower()
            or q in (getattr(i, "genre", "") or "").lower()
            or q in (getattr(i, "title", "") or "").lower()
            or q in str(getattr(i, "year", "") or "").lower()
        ]

    # ── Callbacks ──

    def _on_backfill_done(self, count: int):
        if count > 0 and hasattr(self._win, '_model'):
            self.reload_after_change(reason="backfill")
