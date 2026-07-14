"""File actions — open, scan, drop, and folder import operations.

Refactored for robustness:
  - Single unified flow for add_file (async metadata extraction)
  - scan_multiple() for batched folder scanning
  - Progress reporting via signals
  - Proper thread lifecycle management
"""
import os
import subprocess
import logging

from core.paths import database_path

logger = logging.getLogger("michi.file_actions")


def open_containing_folder(filepath: str) -> bool:
    """Open the file manager at the directory containing the given file."""
    if not filepath:
        return False
    folder = os.path.dirname(filepath)
    if not folder or not os.path.isdir(folder):
        logger.warning("Cannot open containing folder for missing path: %s", filepath)
        return False
    try:
        subprocess.Popen(["xdg-open", folder])
        return True
    except Exception:
        logger.exception("Failed to open containing folder: %s", folder)
        return False


class FileActions:
    def __init__(self, window, services=None):
        self._win = window
        self._svc = services
        self._db = window._db
        self._db_path = database_path()
        self._active_threads: list = []

    def _reload_library(self, reason: str = ""):
        if self._svc and self._svc.reload_library:
            self._svc.reload_library(reason)
        else:
            self._win._reload_library_after_change(reason=reason)

    def _play_file(self, filepath: str):
        if self._svc and self._svc.play_file:
            self._svc.play_file(filepath)
        else:
            self._win._play_file(filepath)

    def _rebuild_sidebar(self):
        if self._svc and self._svc.rebuild_sidebar:
            self._svc.rebuild_sidebar()
        else:
            self._win._rebuild_sidebar()

    def _clear_coverflow_cache(self):
        if self._svc and self._svc.clear_coverflow_cache:
            self._svc.clear_coverflow_cache()
        else:
            self._win._coverflow_cache_key = None

    def _enrich_artist(self, key: str, name: str):
        if self._svc and self._svc.enrich_artist:
            self._svc.enrich_artist(key, name)
        elif hasattr(self._win, '_artist_enrich'):
            self._win._artist_enrich.enrich_artist_by_key(key, name)

    def _get_content(self):
        if self._svc and self._svc.get_content_widget:
            return self._svc.get_content_widget()
        return self._win._content if hasattr(self._win, '_content') else self._win

    def _run_worker(self, name: str, task, on_done=None):
        if self._svc and hasattr(self._svc, 'workers') and self._svc.workers:
            self._svc.workers.run_task(name, task, on_done=on_done)
        elif hasattr(self._win, '_workers'):
            self._win._workers.run_task(name, task, on_done=on_done)
        else:
            task()
            if on_done:
                on_done(None)

    def open_files(self, all_exts: frozenset):
        from PySide6.QtWidgets import QFileDialog
        from ui.toast_notification import ToastNotification
        exts = " ".join(f"*{e}" for e in sorted(all_exts))
        files, _ = QFileDialog.getOpenFileNames(
            self._win, "Abrir archivos", os.path.expanduser("~"),
            f"Multimedia ({exts});;Todos (*)")
        if not files:
            return
        self._add_file_list(files)
        self._reload_library(reason="open_files")
        self._play_file(files[0])
        if len(files) > 1:
            ToastNotification.info(
                f"{len(files)} archivos añadidos", self._win)

    def add_folder(self):
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self._win, "Añadir carpeta", os.path.expanduser("~"))
        if not path:
            return
        self.scan_path(path)

    def scan_multiple(self, paths: list[str]):
        for path in paths:
            self.scan_path(path)

    def folder_create_playlist(self, name: str, filepaths: list):
        pid = self._db.create_playlist(name)
        if pid:
            for fp in filepaths:
                self._db.add_to_playlist(pid, fp)
            self._rebuild_sidebar()
            from ui.toast_notification import ToastNotification
            ToastNotification.success(
                f"Playlist \"{name}\" creada con {len(filepaths)} canciones", self._win)

    def add_files_by_drop(self, urls: list):
        """Process dropped files/folders from drag-and-drop."""
        from library.metadata_extractor import ALL_EXTS
        files = []
        dirs = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                dirs.append(path)
            elif os.path.splitext(path)[1].lower() in ALL_EXTS:
                files.append(path)
        if files:
            self._add_file_list(files)
        if dirs:
            self.scan_multiple(dirs)
        if files or dirs:
            self._win._reload_library_after_change(reason="drop")

    def _add_file_list(self, filepaths: list[str]):
        """Add a list of files to the library, one by one."""
        for fp in filepaths:
            self._db.add_file(fp)

    def add_file_list(self, filepaths: list[str] | None) -> None:
        """Add existing media files to the library from a list of file paths."""
        paths = [fp for fp in (filepaths or []) if fp]
        if not paths:
            return
        self._add_file_list(paths)

    def scan_path(self, path: str):
        from PySide6.QtCore import QThread
        from library.indexer import Indexer
        from ui.loading_overlay import LoadingOverlay
        from ui.toast_notification import ToastNotification

        worker = Indexer.from_db_path(self._db_path, path)
        thread = QThread()

        overlay = LoadingOverlay(self._get_content())
        overlay.set_text("Escaneando...")
        overlay.show(delay_ms=100)

        overlay.cancelled.connect(lambda: self._cancel_scan(thread, worker, overlay))

        worker.progress.connect(
            lambda c, t, f: overlay.set_text(
                f"Escaneando [{c}/{t}]\n{os.path.basename(f)[:60]}"))

        def _on_detail(d):
            skipped = d.get("skipped", 0)
            errors = d.get("errors", 0)
            extra = ""
            if skipped:
                extra += f" · {skipped} sin cambios"
            if errors:
                extra += f" · {errors} errores"
            overlay.set_text(
                f"Escaneando [{d.get('current', 0)}/{d.get('total', 0)}]{extra}\n"
                f"{os.path.basename(d.get('filepath', ''))[:60]}")

        worker.detail.connect(_on_detail)

        worker.enrichment_requested.connect(
            lambda key, name: self._enrich_artist(key, name))

        def _on_done(added):
            overlay.hide()
            overlay.deleteLater()

            def do_cleanup():
                self._db.cleanup_missing_under_root(path)

            def on_cleanup_done(_result):
                self._reload_library(reason="scan")
                self._clear_coverflow_cache()
                ToastNotification.success(
                    f"Escaneo completado: {added} archivos añadidos", self._win)

            self._run_worker("post_scan_cleanup", do_cleanup,
                             on_done=on_cleanup_done)

        worker.moveToThread(thread)
        worker.finished.connect(lambda a: _on_done(a))
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda _=thread: self._cleanup_thread(thread))
        self._active_threads.append(thread)
        thread.start()

    def _cancel_scan(self, thread, worker, overlay):
        worker.cancel()
        thread.quit()
        thread.wait(2000)

    def _cleanup_thread(self, thread):
        if thread in self._active_threads:
            self._active_threads.remove(thread)

    def cancel_all_scans(self):
        for thread in list(self._active_threads):
            thread.requestInterruption()
        self._active_threads.clear()
