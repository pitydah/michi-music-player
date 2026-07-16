"""LibraryService — library loading, tab refresh, filter orchestration."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.library_service")


class LibraryService:
    def __init__(self, db=None, worker_manager=None):
        self._db = db
        self._wm = worker_manager

    def load(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB", "track_count": 0}
        try:
            tc = self._db.conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
            ac = self._db.conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
            arc = self._db.conn.execute("SELECT COUNT(*) FROM artists").fetchone()[0]
            gc = self._db.conn.execute("SELECT COUNT(DISTINCT genre) FROM tracks "
                                       "WHERE genre IS NOT NULL AND genre != ''").fetchone()[0]
            return {"ok": True, "track_count": tc, "album_count": ac,
                    "artist_count": arc, "genre_count": gc}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def reload_after_change(self, reason: str = "") -> dict:
        return self.load()

    def refresh_tab(self, tab: str) -> dict:
        return self.load()

    def refresh_songs(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT filepath, title, artist, album, duration, year, genre "
                "FROM tracks ORDER BY title LIMIT 1000"
            ).fetchall()
            return {"ok": True, "count": len(rows), "items": [
                {"filepath": r[0], "title": r[1], "artist": r[2],
                 "album": r[3], "duration": r[4], "year": r[5], "genre": r[6]}
                for r in rows]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def refresh_albums(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT DISTINCT album, artist, MIN(year) FROM tracks "
                "WHERE album IS NOT NULL AND album != '' "
                "GROUP BY album, artist ORDER BY album LIMIT 1000"
            ).fetchall()
            return {"ok": True, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def refresh_artists(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT DISTINCT artist FROM tracks "
                "WHERE artist IS NOT NULL AND artist != '' "
                "ORDER BY artist LIMIT 1000"
            ).fetchall()
            return {"ok": True, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apply_filters(self, filters: dict | None = None) -> dict:
        return self.refresh_songs()

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
