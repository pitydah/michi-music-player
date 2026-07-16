"""GenresService — genre listing, playback, normalization."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.genres_service")


class GenresService:
    def __init__(self, db=None, playback_service=None):
        self._db = db
        self._playback = playback_service

    def list_genres(self) -> list[dict]:
        if not self._db:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT genre, COUNT(*) as cnt FROM tracks "
                "WHERE genre IS NOT NULL AND genre != '' "
                "GROUP BY genre ORDER BY genre"
            ).fetchall()
            return [{"name": r[0], "count": r[1]} for r in rows]
        except Exception:
            return []

    def play_genre(self, genre: str) -> dict:
        if not self._db or not self._playback:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE"}
        try:
            rows = self._db.conn.execute(
                "SELECT filepath FROM tracks WHERE genre=? ORDER BY title LIMIT 500",
                (genre,)).fetchall()
            if not rows:
                return {"ok": False, "error": "NO_TRACKS"}
            first = rows[0][0]
            self._playback.play(first)
            return {"ok": True, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def normalize_genre(self, old_name: str, new_name: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute(
                "UPDATE tracks SET genre=? WHERE genre=?", (new_name, old_name))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
