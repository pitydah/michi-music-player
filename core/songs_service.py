"""SongsService — track listing, filtering, batch operations."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from audio.player_service import PlayerService
    from core.library.library_query_service import LibraryQueryService
    from core.queue_service import QueueService
    from library.library_db import LibraryDB

logger = logging.getLogger("michi.songs_service")


class SongsService:
    """Provide song listing and user actions for the songs view."""

    def __init__(
        self,
        db: LibraryDB | None = None,
        playback_service: PlayerService | None = None,
        queue_service: QueueService | None = None,
        library_query_service: LibraryQueryService | None = None,
    ) -> None:
        """Initialize the service with its database and action dependencies."""
        self._db = db
        self._playback = playback_service
        self._queue = queue_service
        self._query = library_query_service

    def load(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Load up to 1,000 songs matching the requested filters."""
        if not self._db:
            return {"ok": False, "error": "NO_DB", "items": []}
        try:
            search_query = filters.get("search") if filters else None
            if search_query and self._query:
                items = self._query.search_fts(search_query, limit=1000)
                for field in ("artist", "album", "genre"):
                    if filters.get(field):
                        items = [item for item in items
                                 if item.get(field) == filters[field]]
                return {"ok": True, "count": len(items), "items": items}

            sql = """SELECT filepath, title, artist, album, duration, year, genre
                     FROM media_items WHERE deleted_at IS NULL"""
            params = []
            if filters:
                clauses = []
                if filters.get("artist"):
                    clauses.append("artist=?")
                    params.append(filters["artist"])
                if filters.get("album"):
                    clauses.append("album=?")
                    params.append(filters["album"])
                if filters.get("genre"):
                    clauses.append("genre=?")
                    params.append(filters["genre"])
                if clauses:
                    sql += " AND " + " AND ".join(clauses)
            sql += " ORDER BY title LIMIT 1000"
            rows = self._db.conn.execute(sql, params).fetchall()
            items = [{"filepath": r[0], "title": r[1], "artist": r[2],
                      "album": r[3], "duration": r[4], "year": r[5], "genre": r[6]}
                     for r in rows]
            if search_query:
                needle = str(search_query).casefold()
                items = [item for item in items if any(
                    needle in str(item.get(field, "")).casefold()
                    for field in ("title", "artist", "album")
                )]
            return {"ok": True, "count": len(items), "items": items}
        except Exception as e:
            logger.debug("SongsService.load failed: %s", e)
            return {"ok": False, "error": str(e), "items": []}

    def play_items(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Start playback of the first selected song."""
        if not items or not self._playback:
            return {"ok": False, "error": "NO_ITEMS_OR_PLAYBACK"}
        try:
            for item in items[:1]:
                self._playback.play(item.get("filepath", ""))
            return {"ok": True, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def queue_items(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Append selected songs through the canonical queue service."""
        if not items:
            return {"ok": False, "error": "NO_ITEMS"}
        if self._queue:
            try:
                filepaths = [i.get("filepath", "") for i in items if i.get("filepath")]
                self._queue.enqueue(filepaths, play_now=False)
                return {"ok": True, "count": len(filepaths)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def toggle_favorite(self, filepath: str) -> dict[str, Any]:
        """Toggle favorite status for a song filepath."""
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            cur = self._db.conn.execute(
                "SELECT 1 FROM favorites WHERE track_id=?", (filepath,))
            is_fav = cur.fetchone() is not None
            if is_fav:
                self._db.conn.execute(
                    "DELETE FROM favorites WHERE track_id=?", (filepath,))
            else:
                self._db.conn.execute(
                    "INSERT OR IGNORE INTO favorites (track_id) VALUES (?)", (filepath,))
            return {"ok": True, "favorite": not is_fav}
        except Exception as e:
            logger.debug("SongsService.toggle_favorite failed: %s", e)
            return {"ok": False, "error": str(e)}

    def health(self) -> dict[str, bool]:
        """Report whether the service has an available database."""
        return {"available": self._db is not None}

    def shutdown(self) -> None:
        """Release service resources."""
        return None
