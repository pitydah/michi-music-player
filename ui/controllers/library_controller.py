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
        """Full library load with backfill tasks scheduled (guarded by safe mode + setting)."""
        self.reload_after_change(reason="load")
        if getattr(self._win, '_safe_mode', False):
            return
        from core.settings_manager import get_bool
        if not get_bool("library/auto_backfill_enabled"):
            logger.debug("Backfill skipped: auto_backfill_enabled is False")
            return
        workers = self._win._workers
        if workers:
            workers.run_task("backfill_meta",
                self._win._db.backfill_missing_metadata,
                on_done=self._on_backfill_done)
            workers.run_task("backfill_art",
                self._win._db.backfill_missing_album_art)
            workers.run_task("backfill_genres",
                lambda: self._backfill_genres())

    def reload_after_change(self, reason: str = ""):
        """Centralized data reload entry point for all mutations."""
        w = self._win
        w._all_items = w._db.get_all()
        w._items_index = {i.filepath: i for i in w._all_items}
        w._search_ctrl.set_active("local")
        w._rebuild_sidebar()
        self.refresh_all_tabs(force=True)
        self.refresh_active_tab(force=True)

        self._record_reload_context(reason, len(w._all_items))

        # Refresh songs premium page if it exists
        songs_ctrl = getattr(w, '_songs_ctrl', None)
        if songs_ctrl and hasattr(w, '_songs_premium_page') and w._songs_premium_page:
            songs_ctrl.load()
            vs = songs_ctrl.view_state()
            w._songs_premium_page.load_data(
                vs.items,
                fav_set=set(vs.favorite_track_ids),
                status_cache=dict(vs.status_cache),
            )

    def _record_reload_context(self, reason: str, track_count: int) -> None:
        ctx = getattr(self._win, "_context_svc", None)
        if not ctx:
            return
        reason = reason or "reload"
        if reason in {"scan_finished", "folder_scan", "watcher_scan"}:
            ctx.record_scan_finished({"reason": reason, "tracks": track_count})
        elif reason == "metadata_saved":
            ctx.record_metadata_saved(track_count)
        elif reason.startswith("home_add_music") or reason in {"import_files", "import_playlist"}:
            ctx.record_import_finished(reason=reason, count=track_count)
        else:
            ctx.record_library_reloaded(reason=reason, count=track_count)

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
        w = self._win
        w._song_grid.set_items(w._all_items, card_size=170)
        songs_ctrl = getattr(w, '_songs_ctrl', None)
        if songs_ctrl and hasattr(w, '_songs_premium_page') and w._songs_premium_page:
            songs_ctrl.load(w._all_items)
            vs = songs_ctrl.view_state()
            w._songs_premium_page.load_data(
                vs.items,
                fav_set=set(vs.favorite_track_ids),
                status_cache=dict(vs.status_cache),
            )

    def refresh_albums(self):
        w = self._win
        items = self.album_items()
        if not items:
            w._album_grid.set_items([], 200)
            w._coverflow_cache_key = None
            return

        # Build AlbumRepository as common source
        from library.album_repository import (
            AlbumRepository, album_groups_to_cover_items,
        )
        repo = AlbumRepository()
        repo.build(items)
        w._album_data_repo = repo

        groups = repo.list_groups()
        cover_items = album_groups_to_cover_items(groups, cover_size=200)

        w._album_grid.set_cover_items(cover_items,
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

    def album_items(self) -> list:
        w = self._win
        if not w._all_items and w._db:
            w._all_items = w._db.get_all()
            w._items_index = {i.filepath: i for i in w._all_items}
        return [i for i in w._all_items if getattr(i, "kind", "audio") == "audio"]

    def filtered_album_items(self) -> list:
        items = self.album_items()
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

    # ── Grid display helpers — moved from MainWindow ──

    def show_album_grid(self):
        w = self._win
        items = self.filtered_album_items()
        w._album_grid.set_items(items, 200,
            sort_key=getattr(w, '_album_sort_key', 'title'),
            filter_mode=getattr(w, '_album_filter_mode', 'all'))
        from library.album_art import group_by_album
        groups = group_by_album(items)
        w._count.setText(f"{len(groups)} álbumes")

    def show_song_grid(self):
        w = self._win
        items = w._all_items
        text = getattr(w, '_search_text', "")
        if text:
            q = text.lower()
            items = [i for i in items
                     if q in (i.title or "").lower()
                     or q in (i.artist or "").lower()
                     or q in (i.album or "").lower()
                     or q in (i.filepath or "").lower()]
        w._song_grid.set_items(items, card_size=170)
        w._count.setText(f"{len(items)} canciones")

    def show_library_hub(self, key: str = ""):
        """Lazy-create and display library hub page."""
        w = self._win
        if w._library_hub_page is None:
            from PySide6.QtWidgets import QStackedWidget
            from ui.library.songs_premium_page import SongsPremiumPage
            from ui.controllers.songs_controller import SongsController

            songs_ctrl = getattr(w, '_songs_ctrl', None)
            if songs_ctrl is None:
                svc = getattr(w, '_services', None)
                from core.file_actions import open_containing_folder
                songs_ctrl = SongsController(
                    svc,
                    open_metadata_for_files=w._open_metadata_for_files if hasattr(w, '_open_metadata_for_files') else None,
                    locate_file=open_containing_folder,
                    add_to_playlist_cb=(
                        lambda fps: w._playlist_ctrl.add_files_to_playlist_dialog(fps)
                        if hasattr(w, '_playlist_ctrl') and w._playlist_ctrl
                        else None
                    ),
                    parent=w,
                )
                w._songs_ctrl = songs_ctrl

            w._songs_premium_page = SongsPremiumPage()
            w._songs_premium_page.set_controller(songs_ctrl)

            songs_stack = QStackedWidget()
            songs_stack.addWidget(w._songs_premium_page)
            songs_stack.addWidget(w._song_grid)
            w._songs_stack = songs_stack

            songs_ctrl.load()
            vs = songs_ctrl.view_state()
            w._songs_premium_page.load_data(
                vs.items,
                fav_set=set(vs.favorite_track_ids),
                status_cache=dict(vs.status_cache),
            )

            from ui.hubs.library_hub_page import LibraryHubPage
            w._library_hub_page = LibraryHubPage(
                db=w._db, window=w,
                songs_widget=songs_stack,
                albums_widget=w._albums_stack,
                artists_widget=w._artists_stack,
                genres_widget=w._genres_stack,
                folders_widget=w._folder_browser,
            )
            w._library_hub_page.tab_changed.connect(w._on_library_tab_changed)
        if not w._views.widget("library_hub"):
            w._views.register("library_hub", w._library_hub_page)
        w._fade_content("library_hub")

    def show_folders(self, key: str = ""):
        """Activate folder source and display folder browser."""
        w = self._win
        import os
        from sources.folder_source import FolderSource
        if not hasattr(w, '_folder_source') or w._folder_source is None:
            roots = w._db.get_library_roots() if w._db else []
            start_dir = roots[0] if roots else os.path.expanduser("~")
            w._folder_source = FolderSource(start_dir, db=w._db)
            w._search_ctrl.register("folders", w._folder_source)
        else:
            roots = w._db.get_library_roots() if w._db else []
            if roots:
                current_root = w._folder_source.root
                if current_root not in roots:
                    start_dir = roots[0]
                    w._folder_source.root = start_dir
                    w._search_ctrl.register("folders", w._folder_source)
        w._search_ctrl.set_active("folders")
        w._show_library_hub_page()
        if w._library_hub_page:
            w._library_hub_page.set_current_section("folders")

    def _on_library_tab_changed(self, section_key: str, force: bool = False):
        """Handle library tab switch — update header, lazy-load data."""
        w = self._win
        if section_key == getattr(w, '_last_lib_tab', None) and not force:
            return
        w._last_lib_tab = section_key
        if section_key in ("library", "albums", "artists", "genres", "folders"):
            w._current_section_key = section_key
        from ui.controllers.navigation_controller import resolve_section_config
        config = resolve_section_config(section_key, {})
        views = config.get("views", [])
        default = config.get("default", "list")
        w._view_switcher.show()
        w._view_switcher.set_available_modes(views, default, context=section_key)

        # Register tab change in navigation history (not during history restore)
        nav = getattr(w, '_nav_ctrl', None)
        if nav and not nav.is_restoring:
            nav.push(section_key)

        if section_key == "albums":
            w._show_album_grid()
        elif section_key == "artists":
            w._artist_repo.clear_current()
            w._artist_repo.build(w._all_items)
            w._artist_grid.set_artists(w._artist_repo.groups)
        elif section_key == "genres":
            self.refresh_genres()
        elif section_key == "library":
            w._apply_filters()

    def _backfill_genres(self) -> int:
        try:
            from library.genre_repository import GenreRepository
            repo = GenreRepository(self._win._db.conn)
            count = repo.backfill_from_media_items()
            if count:
                logger.info("Backfilled %d track_genre entries on load", count)
            return count
        except Exception as e:
            logger.warning("backfill_genres failed: %s", e)
            return 0

    # ── Callbacks ──

    def _on_backfill_done(self, count: int):
        if count > 0 and hasattr(self._win, '_model'):
            self.reload_after_change(reason="backfill")
