from __future__ import annotations

import sqlite3
from typing import Any

_GENRE_SORT_WHITELIST = {
    "name": "LOWER(COALESCE(tg.canonical_genre, ''))",
    "track_count": "COUNT(DISTINCT tg.track_id)",
    "album_count": "COUNT(DISTINCT COALESCE(m.album, ''))",
}


class GenreRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def get_all(self) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT tg.canonical_genre as name, "
            "COUNT(DISTINCT tg.track_id) as track_count, "
            "COUNT(DISTINCT COALESCE(m.album, '')) as album_count, "
            "COUNT(DISTINCT COALESCE(m.artist, '')) as artist_count, "
            "COALESCE(SUM(m.duration), 0) as total_duration "
            "FROM track_genres tg "
            "JOIN media_items m ON m.id = tg.track_id AND m.deleted_at IS NULL "
            "GROUP BY tg.canonical_genre "
            "ORDER BY track_count DESC",
        ).fetchall()
        keys = ["name", "track_count", "album_count", "artist_count", "total_duration"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def get_page(self, offset: int = 0, limit: int = 100,
                 sort: str = "track_count", asc: bool = False) -> list[dict[str, Any]]:
        sort_col = _GENRE_SORT_WHITELIST.get(sort, _GENRE_SORT_WHITELIST["track_count"])
        order = "ASC" if asc else "DESC"
        rows = self._conn().execute(
            "SELECT tg.canonical_genre as name, "
            "COUNT(DISTINCT tg.track_id) as track_count, "
            "COUNT(DISTINCT COALESCE(m.album, '')) as album_count, "
            "COUNT(DISTINCT COALESCE(m.artist, '')) as artist_count, "
            "COALESCE(SUM(m.duration), 0) as total_duration "
            "FROM track_genres tg "
            "JOIN media_items m ON m.id = tg.track_id AND m.deleted_at IS NULL "
            "GROUP BY tg.canonical_genre "
            f"ORDER BY {sort_col} {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        keys = ["name", "track_count", "album_count", "artist_count", "total_duration"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def count(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT canonical_genre) FROM track_genres",
        ).fetchone()
        return row[0] if row else 0

    def tracks_for_genre(self, canonical_genre: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, "
            "m.track_number, m.track_uid, "
            "COALESCE(NULLIF(m.album_key, ''), m.album, '') as album_key, m.year "
            "FROM track_genres tg "
            "JOIN media_items m ON m.id = tg.track_id AND m.deleted_at IS NULL "
            "WHERE tg.canonical_genre=? "
            "ORDER BY COALESCE(m.album, ''), COALESCE(m.track_number, 999), m.title",
            (canonical_genre,),
        ).fetchall()
        keys = ["track_id", "filepath", "title", "artist", "album", "duration",
                "track_number", "track_uid", "album_key", "year"]
        return [dict(zip(keys, r, strict=False)) for r in rows]
