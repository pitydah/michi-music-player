from __future__ import annotations

import os
import logging

from library.metadata_extractor import ALL_EXTS

logger = logging.getLogger("michi.library_import")


class LibraryImportService:
    def __init__(self, db, scan_path=None, reload_library=None):
        self._db = db
        self._scan_path = scan_path
        self._reload_library = reload_library

    def add_files(self, filepaths: list[str], reason: str = "import_files") -> int:
        added = 0
        for fp in filepaths:
            ext = os.path.splitext(fp)[1].lower()
            if ext not in ALL_EXTS or not os.path.isfile(fp):
                continue
            try:
                if self._db.add_file(fp):
                    added += 1
            except Exception as e:
                logger.debug("Failed to import file %s: %s", fp, e)
        if added and self._reload_library:
            self._reload_library(reason=reason)
        return added

    def add_folder(self, parent_widget=None) -> str | None:
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            parent_widget or None, "Añadir carpeta", os.path.expanduser("~"))
        if path:
            self.scan_folder(path)
        return path

    def scan_folder(self, path: str) -> None:
        if self._scan_path:
            self._scan_path(path)
