"""LibraryWatcherController — handles FileWatcher signals (add, remove, modify)."""
from __future__ import annotations

import logging

_log = logging.getLogger("michi.lib_watcher")


class LibraryWatcherController:
    """Processes filesystem changes detected by FileWatcher.

    Delegates library mutations to LibraryDB and FileActions,
    then triggers library reload via LibraryController.
    """

    def __init__(self, db, file_actions, library_controller, toast_service=None):
        self._db = db
        self._file_actions = file_actions
        self._lib_ctrl = library_controller
        self._toast = toast_service

    def on_files_added(self, paths: list[str]):
        if not paths:
            return
        try:
            self._file_actions.add_file_list(paths)
            self._lib_ctrl.reload_after_change("watcher_added")
            if self._toast:
                self._toast.show(f"{len(paths)} archivos nuevos detectados", "info")
        except Exception:
            _log.exception("LibraryWatcherController.on_files_added failed")

    def on_files_removed(self, paths: list[str]):
        if not paths:
            return
        try:
            self._db.mark_files_deleted(paths)
            self._lib_ctrl.reload_after_change("watcher_removed")
        except Exception:
            _log.exception("LibraryWatcherController.on_files_removed failed")

    def on_files_modified(self, paths: list[str]):
        if not paths:
            return
        try:
            self._file_actions.add_file_list(paths)
            self._lib_ctrl.reload_after_change("watcher_modified")
        except Exception:
            _log.exception("LibraryWatcherController.on_files_modified failed")
