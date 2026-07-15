"""LibraryDataService — library loading, refresh, backfill scheduling extracted from library_controller."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.library_data")


class LibraryDataService:
    def __init__(self, db=None, worker_manager=None):
        self._db = db
        self._worker_manager = worker_manager

    def load(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB", "track_count": 0}
        try:
            cursor = self._db.conn.execute("SELECT COUNT(*) FROM tracks")
            track_count = cursor.fetchone()[0]
            cursor = self._db.conn.execute("SELECT COUNT(*) FROM albums")
            album_count = cursor.fetchone()[0]
            cursor = self._db.conn.execute("SELECT COUNT(*) FROM artists")
            artist_count = cursor.fetchone()[0]
            return {
                "ok": True,
                "track_count": track_count,
                "album_count": album_count,
                "artist_count": artist_count,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "track_count": 0}

    def reload(self) -> dict:
        return self.load()

    def refresh_tab(self, tab: str) -> dict:
        return self.load()

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
