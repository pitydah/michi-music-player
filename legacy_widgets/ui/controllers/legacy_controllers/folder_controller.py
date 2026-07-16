"""FolderController — orchestrate folder browsing, health, integrity, and maintenance.

Receives signals from FolderBrowserWidget and delegates to services.
Does NOT contain business logic — only coordination.
"""

from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QObject, Signal, QThread, QTimer

from library.folder_health import FolderHealthService
from library.folder_integrity import FolderIntegrityService
from core.file_manager_service import FileManagerService

if TYPE_CHECKING:
    from ui.folder_browser import FolderBrowserWidget

logger = logging.getLogger("michi.folder_controller")


class HealthWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, health_svc, path):
        super().__init__()
        self._svc = health_svc
        self._path = path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return
        try:
            health = self._svc.analyze(self._path)
            self.finished.emit(health)
        except Exception as e:
            self.error.emit(str(e))


class IntegrityWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, svc, path, deep):
        super().__init__()
        self._svc = svc
        self._path = path
        self._deep = deep
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return
        try:
            if self._deep:
                result = self._svc.deep_check(self._path, recursive=True)
            else:
                result = self._svc.quick_check(self._path, recursive=True)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FolderController(QObject):
    """Coordinates folder browsing with health, integrity, and file operations."""

    health_ready = Signal(object)
    integrity_ready = Signal(object)
    scan_started = Signal(str)
    scan_finished = Signal(str, int)
    reindex_finished = Signal(str, int)
    toast_requested = Signal(str, str)
    progress_update = Signal(str, int, int)

    def __init__(self, db=None, file_actions=None, context_svc=None,
                 play_files: Callable | None = None,
                 parent=None):
        super().__init__(parent)
        self._db = db
        self._file_actions = file_actions
        self._context_svc = context_svc
        self._play_files = play_files
        self._health_svc = FolderHealthService(db=db)
        self._integrity_svc = FolderIntegrityService(db=db)
        self._widget: FolderBrowserWidget | None = None
        self._audio_lab_ctrl = None
        self._current_health_thread: QThread | None = None
        self._current_health_worker: HealthWorker | None = None
        self._current_integrity_thread: QThread | None = None
        self._current_integrity_worker: IntegrityWorker | None = None

    def set_audio_lab_controller(self, ctrl):
        self._audio_lab_ctrl = ctrl

    def set_db(self, db):
        self._db = db
        self._health_svc.set_db(db)
        self._integrity_svc.set_db(db)

    def connect(self, widget: FolderBrowserWidget):
        """Wire all widget signals to controller handlers."""
        self._widget = widget
        widget.folder_loaded.connect(self.on_folder_loaded)
        widget.folder_selected.connect(self.on_folder_selected)
        widget.queue_requested.connect(self.on_folder_queued)
        widget.scan_requested.connect(self.on_scan_requested)
        widget.reindex_requested.connect(self.on_reindex_requested)
        widget.add_library_root_requested.connect(self.on_add_library_root_requested)
        widget.integrity_requested.connect(self.on_integrity_requested)
        widget.integrity_deep_requested.connect(self.on_integrity_deep_requested)
        widget.audio_lab_requested.connect(self.on_audio_lab_requested)
        widget.open_file_manager_requested.connect(self.on_open_in_file_manager)
        widget.reveal_file_requested.connect(self.on_reveal_file)
        widget.open_terminal_requested.connect(self.on_open_terminal)
        widget.metadata_folder_requested.connect(self.on_open_metadata_for_folder)
        widget.problem_report_requested.connect(self.on_show_problem_report)
        widget.safe_rename_requested.connect(self.on_safe_rename_requested)
        widget.safe_move_requested.connect(self.on_safe_move_requested)
        logger.debug("FolderController connected to widget")

    def on_folder_loaded(self, path: str):
        if not path or not os.path.isdir(path):
            return
        self._record_context("folder_opened", path)
        self._start_health_worker(path)

    def on_folder_selected(self, filepaths: list[str]):
        if self._play_files:
            self._play_files(filepaths)
        if self._context_svc:
            self._context_svc.record_folder_selected(
                folder_name=self._folder_name(filepaths), count=len(filepaths))

    def on_folder_queued(self, filepaths: list[str]):
        if self._context_svc:
            self._context_svc.record_folder_queued(
                folder_name=self._folder_name(filepaths), count=len(filepaths))

    def on_scan_requested(self, path: str):
        if not path or not os.path.isdir(path):
            return
        self.scan_started.emit(path)
        if self._context_svc:
            self._context_svc.record_folder_scanned(folder_name=path)
        if self._file_actions:
            self._file_actions.scan_path(path)
            self.scan_finished.emit(path, 0)

    def on_reindex_requested(self, path: str):
        if not path or not os.path.isdir(path):
            return
        self._record_context("folder_reindexed", path)
        QTimer.singleShot(0, lambda: self._run_reindex(path))

    def on_add_library_root_requested(self, path: str):
        if not path or not os.path.isdir(path):
            return
        if not self._db:
            self._toast("No hay base de datos conectada", "error")
            return
        try:
            self._db.add_library_root(path)
            self._db.conn.commit()
            self._record_context("folder_added_to_library", path)
            self._toast(
                f"Ra\u00edz de biblioteca agregada: {os.path.basename(path)}", "success")
            if self._file_actions:
                self._file_actions.scan_path(path)
        except Exception as e:
            logger.warning("add_library_root failed: %s", e)
            self._toast(f"Error al agregar ra\u00edz: {e}", "error")

    def on_integrity_requested(self, path: str, deep: bool = False):
        if not path or not os.path.exists(path):
            return
        self._record_context("integrity_checked", path)
        self._start_integrity_worker(path, deep=False)

    def on_integrity_deep_requested(self, path: str):
        if not path or not os.path.exists(path):
            return
        self._record_context("integrity_checked", path)
        self._start_integrity_worker(path, deep=True)

    def on_audio_lab_requested(self, path: str):
        if not self._audio_lab_ctrl:
            self._toast("Audio Lab no est\u00e1 disponible", "warning")
            return
        from library.folder_index import walk_audio_files
        files = walk_audio_files(path)
        if not files:
            self._toast("No se encontraron archivos de audio", "warning")
            return
        try:
            self._audio_lab_ctrl.analyze_filepaths(files)
            self._record_context("folder_sent_to_audio_lab", path)
            self._toast(f"{len(files)} archivos enviados a Audio Lab", "success")
        except Exception as e:
            logger.warning("audio_lab analysis failed: %s", e)
            self._toast(f"Error al enviar a Audio Lab: {e}", "error")

    def on_open_in_file_manager(self, path: str):
        if FileManagerService.open_folder(path):
            self._record_context("folder_opened_in_manager", path)
        else:
            self._toast("No se pudo abrir el gestor de archivos", "warning")

    def on_reveal_file(self, path: str):
        if FileManagerService.reveal_file(path):
            self._record_context("folder_opened_in_manager", path)
        else:
            self._toast("No se pudo revelar el archivo", "warning")

    def on_open_terminal(self, path: str):
        if FileManagerService.open_terminal_here(path):
            self._record_context("terminal_opened", path)
        else:
            self._toast("No se encontr\u00f3 un emulador de terminal", "warning")

    def on_open_metadata_for_folder(self, path: str):
        if self._widget:
            from library.folder_index import list_audio_files
            files = list_audio_files(path)
            if files:
                self._widget.files_for_metadata.emit(files)
            else:
                self._toast("No hay archivos de audio en esta carpeta", "info")

    def on_show_problem_report(self, path: str):
        if not self._widget:
            return
        try:
            health = self._health_svc.analyze(path)
            self._widget.show_problem_report.emit(health)
        except Exception as e:
            logger.warning("problem report failed: %s", e)
            self._toast("Error al generar reporte de problemas", "error")

    def on_safe_rename_requested(self, path: str):
        if self._widget:
            self._widget.safe_rename_dialog.emit(path)

    def on_safe_move_requested(self, path: str):
        if self._widget:
            self._widget.safe_move_dialog.emit(path)

    def _start_health_worker(self, path: str):
        self._cancel_health_worker()
        worker = HealthWorker(self._health_svc, path)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._on_health_done)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(lambda e: logger.warning("Health error: %s", e))
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.started.connect(worker.run)
        self._current_health_worker = worker
        self._current_health_thread = thread
        thread.start()

    def _cancel_health_worker(self):
        if self._current_health_worker:
            self._current_health_worker.cancel()
        if self._current_health_thread and self._current_health_thread.isRunning():
            self._current_health_thread.quit()
            self._current_health_thread.wait(1000)
        self._current_health_worker = None
        self._current_health_thread = None

    def _on_health_done(self, health):
        self.health_ready.emit(health)
        self._current_health_worker = None
        self._current_health_thread = None

    def _start_integrity_worker(self, path: str, deep: bool):
        self._cancel_integrity_worker()
        worker = IntegrityWorker(self._integrity_svc, path, deep)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._on_integrity_done)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(lambda e: logger.warning("Integrity error: %s", e))
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.started.connect(worker.run)
        self._current_integrity_worker = worker
        self._current_integrity_thread = thread
        thread.start()

    def _cancel_integrity_worker(self):
        if self._current_integrity_worker:
            self._current_integrity_worker.cancel()
        if self._current_integrity_thread and self._current_integrity_thread.isRunning():
            self._current_integrity_thread.quit()
            self._current_integrity_thread.wait(1000)
        self._current_integrity_worker = None
        self._current_integrity_thread = None

    def _on_integrity_done(self, result):
        self.integrity_ready.emit(result)
        self._current_integrity_worker = None
        self._current_integrity_thread = None

    def _run_reindex(self, path: str):
        try:
            from library.indexer import Indexer
            from core.paths import database_path
            db_path = database_path()
            indexer = Indexer.from_db_path(db_path, path)
            indexer.run(force=True)
            self.reindex_finished.emit(path, 0)
            self._toast(
                f"Reindexaci\u00f3n completada para {os.path.basename(path)}", "success")
        except Exception as e:
            logger.warning("Reindex failed for %s: %s", path, e)
            self._toast(f"Error al reindexar: {e}", "error")

    @staticmethod
    def _folder_name(filepaths: list[str]) -> str:
        try:
            if filepaths:
                common = os.path.commonpath(filepaths)
                return os.path.basename(common.rstrip("/")) or "Carpeta"
        except Exception:
            pass
        return "Carpeta"

    def _record_context(self, event: str, path: str):
        if not self._context_svc:
            return
        import contextlib
        name = os.path.basename(path.rstrip("/")) or path
        with contextlib.suppress(Exception):
            self._context_svc.record_event(event, {"name": name, "kind": "folder"})

    def _toast(self, message: str, kind: str = "info"):
        self.toast_requested.emit(message, kind)
