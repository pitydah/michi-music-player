"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""
from __future__ import annotations

"""SongsController — coordinates the premium songs view.

Uses AppServices for DB, playback, workers, context, and toast.
Callbacks for metadata editing and file location (UI operations).
"""


import logging
import contextlib
from typing import Callable

from PySide6.QtCore import QObject, Signal

from library.media_item import MediaItem
from library.songs_query_service import SongsQueryService
from library.songs_status_service import SongsStatusService
from library.songs_view_state import SongsFilterState, SongsViewState

logger = logging.getLogger("michi.songs_ctrl")


class SongsController(QObject):
    """Coordinates songs view: load, filter, select, bulk actions.

    Designed to work with AppServices rather than MainWindow directly.
    """

    data_changed = Signal(object)  # SongsViewState
    favorite_changed = Signal(int, bool)  # track_id, is_fav
    import_started = Signal()
    import_finished = Signal(bool, str)  # ok, message

    def __init__(
        self,
        services,  # AppServices-like container with .db, .playback, .workers, .context_svc, .toast
        open_metadata_for_files: Callable[[list[str]], None] | None = None,
        locate_file: Callable[[str], None] | None = None,
        add_to_playlist_cb: Callable[[list[str]], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._services = services
        self._db = getattr(services, 'db', None)
        self._query_svc = SongsQueryService(self._db)
        self._status_svc = SongsStatusService(self._db)
        self._open_metadata_cb = open_metadata_for_files
        self._locate_cb = locate_file
        self._add_to_playlist_cb = add_to_playlist_cb
        self._all_items: list[MediaItem] = []
        self._filtered_items: list[MediaItem] = []
        self._current_filter = SongsFilterState()

    @property
    def query_service(self) -> SongsQueryService:
        return self._query_svc

    @property
    def status_service(self) -> SongsStatusService:
        return self._status_svc

    def status_cache(self) -> dict[int, dict]:
        return self._status_svc.status_cache()

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
        self.data_changed.emit(self.view_state())

    def _refresh_status(self):
        self._status_svc.compute_batch(self._all_items)

    def refresh_audio_lab_badges(self, paths: list[str] | None = None):
        self._status_svc.invalidate_cache_for_paths(paths)
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

        # Convert bitrate from kbps (UI) to bps (DB/MediaItem)
        br = kwargs.get("bitrate_min")
        if br is not None and br < 10000:
            kwargs["bitrate_min"] = br * 1000

        items = self._all_items
        qt = kwargs.get("text_filter", "")
        if qt:
            items = self._query_svc.search(qt)
        items = self._query_svc.filter(items, fav_ids=self._status_svc.favorite_track_ids(), **kwargs)

        # Apply audio_lab_warning post-filter using status cache
        if kwargs.get("only_audio_lab_warning"):
            cache = self._status_svc.status_cache()
            items = [i for i in items if _has_audio_lab_warning(i, cache)]

        self._filtered_items = items
        self.data_changed.emit(self.view_state())
        return items

    def get_display_items(self) -> list[MediaItem]:
        return self._filtered_items

    def view_state(self) -> SongsViewState:
        return SongsViewState(
            items=self._filtered_items,
            favorite_track_ids=frozenset(self._status_svc.favorite_track_ids()),
            status_cache=self._status_svc.status_cache(),
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
        tid = getattr(item, 'id', 0)
        self.favorite_changed.emit(tid, now_fav)
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
            import contextlib
            folder = os.path.dirname(fp)
            if os.path.isdir(folder):
                with contextlib.suppress(Exception):
                    from core.external_process import run_process
                    run_process(["xdg-open", folder])

    def add_to_playlist(self, items: list):
        fps = self._filepaths(items)
        if not fps:
            return
        if self._add_to_playlist_cb:
            self._add_to_playlist_cb(fps)
            return
        # Fallback: show pending toast
        toast = getattr(self._services, 'toast', None)
        if toast and hasattr(toast, 'show'):
            toast.show("Agregar a playlist: usa el menú contextual de la tabla", "info")

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
                    from core.audio_lab.diagnostics_service import analyse_file
                    analyse_file(filepath)
                except Exception:
                    pass
            wm.run_task("analyze_song", lambda f=fp: _run(f))

    # ── Micro Server import (reuses AlbumImportWorker) ──

    def send_to_micro_server(self, items: list):
        from integrations.michi_link.services.import_to_server_service import (
            ImportToServerService,
        )
        svc = ImportToServerService()
        server = getattr(self._services, 'micro_server', None)
        toast = getattr(self._services, 'toast', None)
        if not server:
            if toast and hasattr(toast, 'show'):
                toast.show(
                    "Michi Link no está configurado. Configura un servidor en "
                    "Dispositivos > Michi Sync Suite.", "info")
            return
        fps = self._filepaths(items)
        if not fps:
            if toast and hasattr(toast, 'show'):
                toast.show("No hay archivos para enviar", "error")
            return

        # Preflight
        session_result = svc.create_session(server, fps)
        if not session_result.ok:
            if toast and hasattr(toast, 'show'):
                toast.show(f"Error al preparar envío: {session_result.message}", "error")
            return
        pd = session_result.data
        existing = pd.get("existing", 0)
        needs = pd.get("needs_upload", 0)

        # Dialog — need a parent widget
        from PySide6.QtWidgets import QApplication
        from ui.dialogs.album_server_import_dialog import AlbumServerImportDialog
        parent = QApplication.activeWindow()
        album_title = str(getattr(items[0], "album", "Canciones") if items else "Canciones")
        dlg = AlbumServerImportDialog(
            parent, album_title, len(fps), existing, needs)
        if not dlg.exec() or not dlg.was_confirmed():
            sid = pd.get("session_id", "")
            if sid:
                with contextlib.suppress(Exception):
                    svc.rollback(sid)
            return

        # Use AlbumImportWorker via WorkerManager
        from integrations.michi_link.services.album_import_worker import (
            AlbumImportWorker, AlbumImportProgress, AlbumImportResult,
        )
        wm = getattr(self._services, 'workers', None)
        if not wm:
            if toast and hasattr(toast, 'show'):
                toast.show("Sistema de workers no disponible", "error")
            return

        sid = pd.get("session_id", "")
        worker = AlbumImportWorker(server, fps, import_service=svc, session_id=sid)
        self._active_import_worker = worker

        def _on_progress(progress: AlbumImportProgress):
            dlg.set_progress(progress.current, progress.total)

        def _on_finished(result: AlbumImportResult):
            self._active_import_worker = None
            if result.ok:
                AlbumServerImportDialog.show_report(
                    parent, "Importación completada", result.message, is_error=False)
            else:
                AlbumServerImportDialog.show_report(
                    parent, "Importación fallida", result.message, is_error=True)

        def _on_failed(err: str):
            self._active_import_worker = None
            AlbumServerImportDialog.show_report(
                parent, "Error de importación", err, is_error=True)

        worker.progress.connect(_on_progress)
        worker.finished.connect(_on_finished)
        worker.failed.connect(_on_failed)
        wm.run_task("song_import", worker.run)

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


def _has_audio_lab_warning(item, cache):
    """Check if an item has an Audio Lab warning in its cached status."""
    st = cache.get(getattr(item, 'id', 0), {})
    # Prefer the explicit boolean field
    if st.get("has_audio_lab_warning"):
        return True
    # Fallback: check badge text
    badges = st.get("badges", [])
    return any("warning" in b.lower() or "sospechoso" in b.lower() for b in badges)
