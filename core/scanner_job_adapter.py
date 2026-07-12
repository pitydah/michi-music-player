"""ScannerJobAdapter — ejecuta Indexer con TaskContext (token + progress)."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from core.worker_manager import TaskContext

logger = logging.getLogger("michi.scanner_adapter")


class ScannerJobAdapter:
    def __init__(self, db, library_bridge=None):
        self._db = db
        self._lib = library_bridge

    def scan(self, ctx: TaskContext, folder_path: str) -> dict:
        result = {
            "files_seen": 0, "added": 0, "updated": 0,
            "unchanged": 0, "skipped": 0, "errors": 0,
            "missing": 0, "elapsed": 0, "error_code": "",
        }
        if not self._db or not folder_path:
            result["error_code"] = "NO_DB_OR_PATH"
            return result
        p = Path(folder_path)
        if not p.is_dir():
            result["error_code"] = "DIR_NOT_FOUND"
            return result
        try:
            ctx.token.raise_if_cancelled()
            start = time.time()
            from library.indexer import Indexer
            worker = Indexer(self._db, str(p))
            worker.run()
            ctx.token.raise_if_cancelled()
            if hasattr(self._db, 'conn') and self._db.conn:
                self._db.conn.commit()
            if self._lib and hasattr(self._lib, 'refresh'):
                self._lib.refresh()
            result["elapsed"] = time.time() - start
            result["added"] = getattr(worker, 'added_count', 0)
        except Exception as e:
            if ctx.token.is_cancelled():
                result["error_code"] = "CANCELLED"
            else:
                logger.exception("Scan failed: %s", e)
                result["error_code"] = "SCAN_FAILED"
        return result
