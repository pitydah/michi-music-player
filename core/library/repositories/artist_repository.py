from __future__ import annotations

import sqlite3
from typing import Any

_ARTIST_SORT_WHITELIST = {
    "name": "LOWER(COALESCE(NULLIF(m.albumartist,''), m.artist, ''))",
    "track_count": "COUNT(*)",
    "album_count": "COUNT(DISTINCT COALESCE(m.album, ''))",
    "duration": "SUM(COALESCE(m.duration, 0))",
}

_ARTIST_SELECT = (
    "COALESCE(NULLIF(m.albumartist,''), m.artist, '') as artist_name, "
    "COUNT(*) as track_count, "
    "COUNT(DISTINCT COALESCE(m.album, '')) as album_count, "
    "SUM(COALESCE(m.duration, 0)) as total_duration, "
    "MAX(m.year) as year, "
    "MAX(m.genre) as genre"
)


class ArtistRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        where = (
            "m.deleted_at IS NULL AND "
            "(COALESCE(NULLIF(m.albumartist,''), m.artist, '')=? OR m.artist=?)"
        )
        row = self._conn().execute(
            f"SELECT {_ARTIST_SELECT} "
            "FROM media_items m "
            f"WHERE {where} "
            "GROUP BY artist_name",
            (name, name),
        ).fetchone()
        if not row:
            return None
        keys = ["artist_name", "track_count", "album_count",
                "total_duration", "year", "genre"]
        return dict(zip(keys, row, strict=False))

    def get_page(self, offset: int = 0, limit: int = 100,
                 sort: str = "name", asc: bool = True) -> list[dict[str, Any]]:
        sort_col = _ARTIST_SORT_WHITELIST.get(sort, _ARTIST_SORT_WHITELIST["name"])
        order = "ASC" if asc else "DESC"
        rows = self._conn().execute(
            f"SELECT {_ARTIST_SELECT} "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.artist, '') != '' "
            "GROUP BY artist_name "
            f"ORDER BY {sort_col} {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        keys = ["artist_name", "track_count", "album_count",
                "total_duration", "year", "genre"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def count(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(albumartist,''), artist, '')) "
            "FROM media_items WHERE deleted_at IS NULL AND COALESCE(artist, '') != ''",
        ).fetchone()
        return row[0] if row else 0

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        p = f"%{query}%"
        rows = self._conn().execute(
            f"SELECT {_ARTIST_SELECT} "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.artist, '') != '' "
            "AND (COALESCE(NULLIF(m.albumartist,''), m.artist, '') LIKE ? OR m.artist LIKE ?) "
            "GROUP BY artist_name LIMIT ?",
            (p, p, limit),
        ).fetchall()
        keys = ["artist_name", "track_count", "album_count",
                "total_duration", "year", "genre"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def albums_for_artist(self, artist_name: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT DISTINCT COALESCE(NULLIF(m.album_key, ''), m.album, '') as album_key, "
            "m.album as album_title, "
            "COUNT(*) as track_count, MIN(m.year) as year, MAX(m.genre) as genre "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.album, '') != '' "
            "AND (COALESCE(NULLIF(m.albumartist,''), m.artist, '')=? OR m.artist=?) "
            "GROUP BY album_key ORDER BY MIN(m.year), m.album",
            (artist_name, artist_name),
        ).fetchall()
        keys = ["album_key", "album_title", "track_count", "year", "genre"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def tracks_for_artist(self, artist_name: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, "
            "m.track_number, m.track_uid, "
            "COALESCE(NULLIF(m.album_key, ''), m.album, '') as album_key, m.year, m.genre "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL "
            "AND (COALESCE(NULLIF(m.albumartist,''), m.artist, '')=? OR m.artist=?) "
            "ORDER BY COALESCE(m.album, ''), COALESCE(m.track_number, 999), m.title",
            (artist_name, artist_name),
        ).fetchall()
        keys = ["track_id", "filepath", "title", "artist", "album", "duration",
                "track_number", "track_uid", "album_key", "year", "genre"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def compilations(self, artist_name: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT DISTINCT COALESCE(NULLIF(m.album_key, ''), m.album, '') as album_key, "
            "m.album as album_title, "
            "COUNT(*) as track_count, MIN(m.year) as year "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.album, '') != '' "
            "AND m.artist=? AND m.compilation=1 "
            "GROUP BY album_key ORDER BY MIN(m.year), m.album",
            (artist_name,),
        ).fetchall()
        keys = ["album_key", "album_title", "track_count", "year"]
        return [dict(zip(keys, r, strict=False)) for r in rows]
