"""LibrarySourcesService — canonico, persistente via LibraryDB.library_roots."""
from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger("michi.library_sources")


class LibrarySourcesService:
    def __init__(self, db=None):
        self._db = db

    def list(self) -> list[dict]:
        if not self._db or not hasattr(self._db, 'get_library_roots'):
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT path, enabled, created_at, updated_at, last_scan,"
                "       file_count, added_count, updated_count, missing_count, error_code "
                "FROM library_roots ORDER BY path"
            ).fetchall()
            return [
                {
                    "path": r[0], "enabled": bool(r[1]),
                    "available": Path(r[0]).is_dir() if r[0] else False,
                    "created_at": r[2] or 0, "updated_at": r[3] or 0,
                    "last_scan": r[4] or 0,
                    "file_count": r[5] or 0, "added_count": r[6] or 0,
                    "updated_count": r[7] or 0, "missing_count": r[8] or 0,
                    "error_code": r[9] or "",
                }
                for r in rows
            ]
        except Exception:
            return []

    def add(self, path: str) -> dict:
        if not path or not Path(path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        if not self._db or not hasattr(self._db, 'add_library_root'):
            return {"ok": False, "error": "NO_DB"}
        if self._db.add_library_root(path):
            return {"ok": True}
        return {"ok": False, "error": "ALREADY_EXISTS"}

    def remove(self, path: str) -> dict:
        if not self._db or not hasattr(self._db, 'remove_library_root'):
            return {"ok": False, "error": "NO_DB"}
        if self._db.remove_library_root(path):
            return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def enable(self, path: str, enabled: bool) -> dict:
        if not self._db or not hasattr(self._db, 'conn'):
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute(
                "UPDATE library_roots SET enabled=? WHERE path=?",
                (int(enabled), path)
            )
            self._db.conn.commit()
            return {"ok": True}
        except Exception:
            return {"ok": False, "error": "UPDATE_FAILED"}

    def root_paths(self) -> list[str]:
        if not self._db or not hasattr(self._db, 'get_library_roots'):
            try:
                from core.settings_manager import get
                folder = get("general/music_folder")
                if folder and Path(folder).is_dir():
                    return [folder]
            except Exception:
                pass
            return []
        return [s["path"] for s in self.list() if s["enabled"] and s["available"]]

    def update_scan_stats(self, path: str, stats: dict):
        if not self._db or not hasattr(self._db, 'conn'):
            return
        try:
            now = time.time()
            self._db.conn.execute(
                "UPDATE library_roots SET last_scan=?, file_count=?, added_count=?,"
                " updated_count=?, missing_count=?, error_code=?, updated_at=? WHERE path=?",
                (now, stats.get("file_count", 0), stats.get("added", 0),
                 stats.get("updated", 0), stats.get("missing", 0),
                 stats.get("error_code", ""), now, path)
            )
            self._db.conn.commit()
        except Exception:
            pass
