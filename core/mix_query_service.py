"""MixQueryService — SQL-based mix queries, no fetch_all."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.mix_query")


class MixQueryService:
    def __init__(self, db=None):
        self._db = db

    def fetch_tracks(self, sql: str, params: list, limit: int = 50) -> list[dict]:
        if not self._db:
            return []
        try:
            rows = self._db.conn.execute(
                f"{sql} LIMIT ?", params + [limit]
            ).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0}
                for r in rows
            ]
        except Exception:
            return []

    def favorites(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m JOIN favorites f ON m.filepath = f.track_id "
            "WHERE m.deleted_at IS NULL ORDER BY f.added_at DESC", [], limit)

    def recent(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.last_played > 0 "
            "ORDER BY m.last_played DESC", [], limit)

    def most_played(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.play_count > 0 "
            "ORDER BY m.play_count DESC", [], limit)

    def unplayed(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND "
            "(m.play_count IS NULL OR m.play_count = 0) "
            "ORDER BY m.created_at DESC", [], limit)

    def genre(self, genre: str, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.genre = ? "
            "ORDER BY m.created_at DESC", [genre], limit)
