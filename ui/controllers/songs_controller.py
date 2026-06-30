"""SongsController — coordinates the premium songs view.

Uses AppServices for DB, playback, workers, context, and toast.
Callbacks for metadata editing and file location (UI operations).
"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject

from library.media_item import MediaItem
from library.songs_query_service import SongsQueryService
from library.songs_status_service import SongsStatusService
from library.songs_view_state import SongsFilterState, SongsViewState

logger = logging.getLogger("michi.songs_ctrl")


class SongsController(QObject):
    """Coordinates songs view: load, filter, select, bulk actions.

    Designed to work with AppServices rather than MainWindow directly.
    """

    def __init__(
        self,
        services,  # AppServices-like container with .db, .playback, .workers, .context_svc, .toast
        open_metadata_for_files: Callable[[list[str]], None] | None = None,
        locate_file: Callable[[str], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._services = services
        self._db = getattr(services, 'db', None)
        self._query_svc = SongsQueryService(self._db)
        self._status_svc = SongsStatusService(self._db)
        self._open_metadata_cb = open_metadata_for_files
        self._locate_cb = locate_file
        self._all_items: list[MediaItem] = []
        self._filtered_items: list[MediaItem] = []
        self._current_filter = SongsFilterState()

    @property
    def query_service(self) -> SongsQueryService:
        return self._query_svc

    @property
    def status_service(self) -> SongsStatusService:
        return self._status_svc

    def load(self, items: list[MediaItem] | None = None):
        """Load songs, compute status, refresh favorites."""
        if items is not None:
            self._all_items = list(items)
        elif self._db:
            self._all_items = self._query_svc.fetch_all()
        else:
            self._all_items = []
        self._filtered_items = list(self._all_items)
        self._status_svc.invalidate_cache()
        self._status_svc.refresh_favorites()
        self._refresh_status()

    def _refresh_status(self):
        self._status_svc.compute_batch(self._all_items)

    def apply_filter(self, filter_state: SongsFilterState | None = None,
                     text: str = "", **filters):
        if filter_state is not None:
            self._current_filter = filter_state
            kwargs = filter_state.to_query_kwargs()
        else:
            kwargs = dict(filters)
            if text:
                kwargs["text_filter"] = text

        items = self._all_items
        qt = kwargs.get("text_filter", "")
        if qt:
            items = self._query_svc.search(qt)
        items = self._query_svc.filter(items, fav_ids=self._status_svc.favorite_track_ids(), **kwargs)
        self._filtered_items = items
        return items

    def get_display_items(self) -> list[MediaItem]:
        return self._filtered_items

    def view_state(self) -> SongsViewState:
        return SongsViewState(
            items=self._filtered_items,
            favorite_track_ids=frozenset(self._status_svc.favorite_track_ids()),
            status_cache=dict(self._status_svc._quality_cache),
            filter_state=self._current_filter,
        )

    # ── Bulk actions ──

    def _filepaths(self, items: list) -> list[str]:
        return [i.filepath for i in items if hasattr(i, 'filepath') and i.filepath]

    def play_items(self, items: list):
        fps = self._filepaths(items)
        if not fps:
            return
        pb = getattr(self._services, 'playback', None)
        if pb and hasattr(pb, 'play_queue'):
            pb.play_queue(fps)
        elif pb:
            pb.enqueue(fps, play_now=True)

    def queue_items(self, items: list):
        fps = self._filepaths(items)
        if not fps:
            return
        pb = getattr(self._services, 'playback', None)
        if pb:
            pb.enqueue(fps, play_now=False)

    def toggle_favorite(self, item):
        fp = getattr(item, 'filepath', '')
        if not fp or not self._db:
            return
        try:
            now_fav = self._db.toggle_favorite(fp)
        except Exception:
            return
        self._status_svc.refresh_favorites()
        ctx = getattr(self._services, 'context_svc', None)
        if ctx:
            ctx.record_favorite_changed(track=item, favorite=now_fav)
        toast = getattr(self._services, 'toast', None)
        if toast and hasattr(toast, 'show'):
            label = "★ Favorito" if now_fav else "☆ Favorito removido"
            toast.show(label, "success")

    def edit_metadata(self, items: list):
        fps = self._filepaths(items)
        if fps and self._open_metadata_cb:
            self._open_metadata_cb(fps)

    def locate_file(self, item):
        fp = getattr(item, 'filepath', '')
        if fp and self._locate_cb:
            self._locate_cb(fp)
        elif fp:
            import os
            import subprocess
            import contextlib
            folder = os.path.dirname(fp)
            if os.path.isdir(folder):
                with contextlib.suppress(Exception):
                    subprocess.Popen(["xdg-open", folder])

    def add_to_playlist(self, items: list):
        fps = self._filepaths(items)
        if fps:
            from ui.controllers.playlist_controller import PlaylistController
            ctrl = PlaylistController(self._services)
            ctrl.create_playlist_from_tracks(fps, "Nueva playlist")

    def analyze_quality(self, items: list):
        fps = self._filepaths(items)
        if not fps:
            return
        wm = getattr(self._services, 'workers', None)
        if not wm:
            return
        for fp in fps:
            def _run(filepath):
                try:
                    from ui.audio_lab.diagnostics_service import analyse_file
                    analyse_file(filepath)
                except Exception:
                    pass
            wm.run_task("analyze_song", lambda f=fp: _run(f))

    # ── Placeholder actions (not yet fully implemented) ──

    def send_to_micro_server(self, items: list):
        """Placeholder: send tracks to Michi Micro Server."""
        toast = getattr(self._services, 'toast', None)
        if toast and hasattr(toast, 'show'):
            toast.show("Enviar a Micro Server: pendiente", "info")

    def sync_to_mobile(self, items: list):
        """Placeholder: sync tracks to Michi Mobile."""
        toast = getattr(self._services, 'toast', None)
        if toast and hasattr(toast, 'show'):
            toast.show("Sincronizar a móvil: pendiente", "info")

    def convert_items(self, items: list):
        """Placeholder: convert tracks to another format."""
        toast = getattr(self._services, 'toast', None)
        if toast and hasattr(toast, 'show'):
            toast.show("Conversión de formato: pendiente", "info")
