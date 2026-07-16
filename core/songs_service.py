"""SongsService — track listing, filtering, batch operations."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.songs_service")


class SongsService:
    def __init__(self, db=None, playback_service=None, library_query_service=None):
        self._db = db
        self._playback = playback_service
        self._query = library_query_service

    def load(self, filters: dict | None = None) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB", "items": []}
        try:
            sql = "SELECT filepath, title, artist, album, duration, year, genre FROM tracks"
            params = []
            where_clauses = []
            if filters:
                if filters.get("artist"):
                    where_clauses.append("artist=?")
                    params.append(filters["artist"])
                if filters.get("album"):
                    where_clauses.append("album=?")
                    params.append(filters["album"])
                if filters.get("genre"):
                    where_clauses.append("genre=?")
                    params.append(filters["genre"])
                if filters.get("search"):
                    where_clauses.append("(title LIKE ? OR artist LIKE ? OR album LIKE ?)")
                    s = f"%{filters['search']}%"
                    params.extend([s, s, s])
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            sql += " ORDER BY title LIMIT 1000"
            rows = self._db.conn.execute(sql, params).fetchall()
            items = [{"filepath": r[0], "title": r[1], "artist": r[2],
                      "album": r[3], "duration": r[4], "year": r[5], "genre": r[6]}
                     for r in rows]
            return {"ok": True, "count": len(items), "items": items}
        except Exception as e:
            return {"ok": False, "error": str(e), "items": []}

    def play_items(self, items: list[dict]) -> dict:
        if not items or not self._playback:
            return {"ok": False, "error": "NO_ITEMS_OR_PLAYBACK"}
        try:
            for item in items[:1]:
                self._playback.play(item.get("filepath", ""))
            return {"ok": True, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def queue_items(self, items: list[dict]) -> dict:
        if not items:
            return {"ok": False, "error": "NO_ITEMS"}
        if self._playback and hasattr(self._playback, 'enqueue'):
            try:
                filepaths = [i.get("filepath", "") for i in items if i.get("filepath")]
                self._playback.enqueue(filepaths, play_now=False)
                return {"ok": True, "count": len(filepaths)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def toggle_favorite(self, filepath: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            cur = self._db.conn.execute("SELECT favorite FROM tracks WHERE filepath=?", (filepath,))
            row = cur.fetchone()
            if row is None:
                return {"ok": False, "error": "TRACK_NOT_FOUND"}
            new_val = 0 if row[0] else 1
            self._db.conn.execute("UPDATE tracks SET favorite=? WHERE filepath=?", (new_val, filepath))
            return {"ok": True, "favorite": bool(new_val)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
