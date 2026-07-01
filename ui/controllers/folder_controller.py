"""FolderController — orchestrate folder browsing, health, integrity, and maintenance.

Receives signals from FolderBrowserWidget and delegates to services.
Does NOT contain business logic — only coordination.
"""

from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QTimer

from library.folder_health import FolderHealthService
from library.folder_integrity import FolderIntegrityService
from core.file_manager_service import FileManagerService

if TYPE_CHECKING:
    from ui.folder_browser import FolderBrowserWidget

logger = logging.getLogger("michi.folder_controller")


class FolderController(QObject):
    """Coordinates folder browsing with health, integrity, and file operations."""

    health_ready = Signal(object)       # FolderHealth
    integrity_ready = Signal(object)    # FolderIntegrityResult
    scan_started = Signal(str)
    scan_finished = Signal(str, int)
    reindex_finished = Signal(str, int)
    toast_requested = Signal(str, str)  # message, type (info/success/warning/error)
    progress_update = Signal(str, int, int)  # label, current, total

    def __init__(self, db=None, file_actions=None, context_svc=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._file_actions = file_actions
        self._context_svc = context_svc
        self._health_svc = FolderHealthService(db=db)
        self._integrity_svc = FolderIntegrityService(db=db)
        self._widget: FolderBrowserWidget | None = None

    def set_db(self, db):
        self._db = db
        self._health_svc.set_db(db)
        self._integrity_svc.set_db(db)

    def connect(self, widget: FolderBrowserWidget):
        """Wire widget signals to controller handlers."""
        self._widget = widget
        widget.folder_loaded.connect(self.on_folder_loaded)
        widget.reindex_requested.connect(self.on_reindex_requested)
        widget.add_library_root_requested.connect(self.on_add_library_root_requested)
        widget.integrity_requested.connect(self.on_integrity_requested)
        widget.integrity_deep_requested.connect(self.on_integrity_deep_requested)
        widget.open_file_manager_requested.connect(self.on_open_in_file_manager)
        widget.reveal_file_requested.connect(self.on_reveal_file)
        widget.open_terminal_requested.connect(self.on_open_terminal)
        widget.metadata_folder_requested.connect(self.on_open_metadata_for_folder)
        widget.problem_report_requested.connect(self.on_show_problem_report)
        widget.safe_rename_requested.connect(self.on_safe_rename_requested)
        widget.safe_move_requested.connect(self.on_safe_move_requested)
        logger.debug("FolderController connected to widget")

    def on_folder_loaded(self, path: str):
        """When a folder is loaded, analyze its health in a background task."""
        if not path or not os.path.isdir(path):
            return
        self._record_context("folder_opened", path)
        QTimer.singleShot(0, lambda: self._run_health_analysis(path))

    def on_folder_selected(self, filepaths: list[str]):
        """Handle file selection for playback."""
        if self._context_svc:
            self._context_svc.record_folder_selected(
                folder_name=self._folder_name(filepaths),
                count=len(filepaths),
            )

    def on_folder_queued(self, filepaths: list[str]):
        """Handle file queue request."""
        if self._context_svc:
            self._context_svc.record_folder_queued(
                folder_name=self._folder_name(filepaths),
                count=len(filepaths),
            )

    def on_scan_requested(self, path: str):
        """Request a scan of the folder."""
        if not path or not os.path.isdir(path):
            return
        self.scan_started.emit(path)
        if self._context_svc:
            self._context_svc.record_folder_scanned(folder_name=path)
        if self._file_actions:
            self._file_actions.scan_path(path)
            self.scan_finished.emit(path, 0)

    def on_reindex_requested(self, path: str):
        """Request metadata reindexing of a folder."""
        if not path or not os.path.isdir(path):
            return
        self._record_context("folder_reindexed", path)
        self._run_reindex(path)

    def on_add_library_root_requested(self, path: str):
        """Add a folder as a library root and scan it."""
        if not path or not os.path.isdir(path):
            return
        if not self._db:
            self._toast("No hay base de datos conectada", "error")
            return
        try:
            self._db.add_library_root(path)
            self._db.conn.commit()
            self._record_context("folder_added_to_library", path)
            self._toast(f"Raíz de biblioteca agregada: {os.path.basename(path)}", "success")
            if self._file_actions:
                self._file_actions.scan_path(path)
        except Exception as e:
            logger.warning("add_library_root failed: %s", e)
            self._toast(f"Error al agregar raíz: {e}", "error")

    def on_integrity_requested(self, path: str, deep: bool = False):
        """Run integrity check on a folder."""
        if not path or not os.path.exists(path):
            return
        self._record_context("integrity_checked", path)
        QTimer.singleShot(0, lambda: self._run_integrity(path, deep=False))

    def on_integrity_deep_requested(self, path: str):
        """Run deep integrity check."""
        if not path or not os.path.exists(path):
            return
        self._record_context("integrity_checked", path)
        QTimer.singleShot(0, lambda: self._run_integrity(path, deep=True))

    def on_open_in_file_manager(self, path: str):
        """Open folder in system file manager."""
        if FileManagerService.open_folder(path):
            self._record_context("folder_opened_in_manager", path)
        else:
            self._toast("No se pudo abrir el gestor de archivos", "warning")

    def on_reveal_file(self, path: str):
        """Reveal/highlight file in file manager."""
        if FileManagerService.reveal_file(path):
            self._record_context("folder_opened_in_manager", path)
        else:
            self._toast("No se pudo revelar el archivo", "warning")

    def on_open_terminal(self, path: str):
        """Open terminal emulator at the given path."""
        if FileManagerService.open_terminal_here(path):
            self._record_context("terminal_opened", path)
        else:
            self._toast("No se encontró un emulador de terminal", "warning")

    def on_open_metadata_for_folder(self, path: str):
        """Signal to open metadata editor for files in this folder."""
        if self._widget:
            from library.folder_index import list_audio_files
            files = list_audio_files(path)
            if files:
                self._widget.files_for_metadata.emit(files)

    def on_show_problem_report(self, path: str):
        """Request showing problem report for a folder."""
        if self._widget:
            result = self._health_svc.analyze(path)
            self._widget.show_problem_report.emit(result)

    def on_safe_rename_requested(self, path: str):
        """Request safe rename dialog for a folder."""
        if self._widget:
            self._widget.safe_rename_dialog.emit(path)

    def on_safe_move_requested(self, path: str):
        """Request safe move dialog for a folder."""
        if self._widget:
            self._widget.safe_move_dialog.emit(path)

    def _run_health_analysis(self, path: str):
        try:
            health = self._health_svc.analyze(path)
            self.health_ready.emit(health)
        except Exception as e:
            logger.warning("Health analysis failed for %s: %s", path, e)

    def _run_integrity(self, path: str, deep: bool = False):
        try:
            if deep:
                result = self._integrity_svc.deep_check(path, recursive=True)
            else:
                result = self._integrity_svc.quick_check(path, recursive=True)
            self.integrity_ready.emit(result)
        except Exception as e:
            logger.warning("Integrity check failed for %s: %s", path, e)

    def _run_reindex(self, path: str):
        try:
            from library.indexer import Indexer
            from core.paths import database_path
            db_path = database_path()
            indexer = Indexer.from_db_path(db_path, path)
            indexer.run()
            self.reindex_finished.emit(path, 0)
            self._toast(f"Reindexación completada para {os.path.basename(path)}", "success")
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
            self._context_svc.record_event(event, {"path": path, "name": name})

    def _toast(self, message: str, kind: str = "info"):
        self.toast_requested.emit(message, kind)
