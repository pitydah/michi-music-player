"""SongsController — coordinates the premium songs view.

Loads songs via SongsQueryService, applies filters, manages selection,
executes bulk actions, and updates context.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from library.songs_query_service import SongsQueryService
from library.songs_status_service import SongsStatusService

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.songs_ctrl")


class SongsController(QObject):
    """Coordinates songs view: load, filter, select, bulk actions."""

    def __init__(self, window: MainWindow):
        super().__init__(window)
        self._win = window
        self._query_svc = SongsQueryService(window._db if hasattr(window, '_db') else None)
        self._status_svc = SongsStatusService(window._db if hasattr(window, '_db') else None)
        self._all_items: list = []
        self._filtered_items: list = []

    @property
    def query_service(self) -> SongsQueryService:
        return self._query_svc

    @property
    def status_service(self) -> SongsStatusService:
        return self._status_svc

    def load(self):
        """Load all songs and compute status badges."""
        w = self._win
        if not hasattr(w, '_all_items'):
            self._all_items = self._query_svc.fetch_all()
        else:
            self._all_items = list(getattr(w, '_all_items', []))
        self._filtered_items = list(self._all_items)
        self._status_svc.refresh_favorites()
        self._refresh_status()

    def _refresh_status(self):
        """Compute status badges for all loaded items."""
        self._status_svc.compute_batch(self._all_items)

    def apply_filter(self, text: str = "", **filters):
        """Apply search text and/or advanced filters."""
        items = self._all_items
        if text:
            items = self._query_svc.search(text)
        items = self._query_svc.filter(items, **filters)
        self._filtered_items = items
        return items

    def get_display_items(self) -> list:
        return self._filtered_items

    # ── Bulk actions ──

    def play_items(self, items: list):
        """Play a list of MediaItems."""
        w = self._win
        fps = [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]
        if fps and hasattr(w, '_playback_ctrl') and w._playback_ctrl:
            w._playback_ctrl.play_filepaths(fps, play_now=True)

    def queue_items(self, items: list):
        """Queue a list of MediaItems."""
        w = self._win
        fps = [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]
        if fps and hasattr(w, '_playback_ctrl') and w._playback_ctrl:
            w._playback_ctrl.enqueue_with_context(fps, play_now=False, source="songs")

    def toggle_favorite(self, item):
        """Toggle favorite status for a single item."""
        w = self._win
        fp = getattr(item, 'filepath', '')
        if not fp or not hasattr(w, '_db'):
            return
        db = w._db
        try:
            now_fav = db.toggle_favorite(fp)
        except Exception:
            return
        self._status_svc.refresh_favorites()
        ctx = getattr(w, '_context_svc', None)
        if ctx:
            ctx.record_favorite_changed(track=item, favorite=now_fav)

    def edit_metadata(self, items: list):
        """Open metadata editor for selected items."""
        w = self._win
        fps = [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]
        if fps and hasattr(w, '_artist_ctrl'):
            w._artist_ctrl.open_metadata_for_files(fps)

    def locate_file(self, item):
        """Open file manager at the item's location."""
        fp = getattr(item, 'filepath', '')
        if fp:
            import os
            import subprocess
            import contextlib
            folder = os.path.dirname(fp)
            if os.path.isdir(folder):
                with contextlib.suppress(Exception):
                    subprocess.Popen(["xdg-open", folder])
