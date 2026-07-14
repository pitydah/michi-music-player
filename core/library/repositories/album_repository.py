from __future__ import annotations

import sqlite3
from typing import Any

_ALBUM_SORT_WHITELIST = {
    "year": "MIN(m.year)",
    "title": "LOWER(COALESCE(MIN(m.album), ''))",
    "artist": "LOWER(COALESCE(MIN(NULLIF(m.albumartist,'')), MIN(m.artist), ''))",
    "duration": "SUM(COALESCE(m.duration, 0))",
    "track_count": "COUNT(*)",
    "added": "MAX(COALESCE(m.created_at, 0))",
}

_ALBUM_SELECT = (
    "COALESCE(NULLIF(m.album_key, ''), m.album, '') as album_key, "
    "m.album as album_title, "
    "COALESCE(NULLIF(m.albumartist,''), m.artist, '') as album_artist, "
    "MIN(m.year) as year, "
    "COUNT(*) as track_count, "
    "SUM(COALESCE(m.duration, 0)) as total_duration, "
    "MAX(m.genre) as genre, "
    "COUNT(DISTINCT COALESCE(m.disc_number, 1)) as disc_count"
)


class AlbumRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def get_by_key(self, album_key: str) -> dict[str, Any] | None:
        row = self._conn().execute(
            f"SELECT {_ALBUM_SELECT} "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL "
            "AND COALESCE(NULLIF(m.album_key, ''), m.album, '')=? "
            "GROUP BY album_key",
            (album_key,),
        ).fetchone()
        if not row:
            return None
        keys = ["album_key", "album_title", "album_artist", "year",
                "track_count", "total_duration", "genre", "disc_count"]
        return dict(zip(keys, row, strict=False))

    def get_page(self, offset: int = 0, limit: int = 100,
                 sort: str = "year", asc: bool = False) -> list[dict[str, Any]]:
        sort_col = _ALBUM_SORT_WHITELIST.get(sort, _ALBUM_SORT_WHITELIST["year"])
        order = "ASC" if asc else "DESC"
        rows = self._conn().execute(
            f"SELECT {_ALBUM_SELECT} "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.album, '') != '' "
            "GROUP BY album_key "
            f"ORDER BY {sort_col} {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        keys = ["album_key", "album_title", "album_artist", "year",
                "track_count", "total_duration", "genre", "disc_count"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def count(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(album_key, ''), album, '')) "
            "FROM media_items WHERE deleted_at IS NULL AND COALESCE(album,'') != ''",
        ).fetchone()
        return row[0] if row else 0

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        p = f"%{query}%"
        rows = self._conn().execute(
            f"SELECT {_ALBUM_SELECT} "
            "FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.album, '') != '' "
            "AND (m.album LIKE ? OR m.album_key LIKE ? OR "
            "     COALESCE(NULLIF(m.albumartist,''), m.artist, '') LIKE ?) "
            "GROUP BY album_key LIMIT ?",
            (p, p, p, limit),
        ).fetchall()
        keys = ["album_key", "album_title", "album_artist", "year",
                "track_count", "total_duration", "genre", "disc_count"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def tracks_for_album(self, album_key: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT id, filepath, title, artist, album, duration, "
            "track_number, disc_number, track_uid, album_key, year, genre "
            "FROM media_items WHERE deleted_at IS NULL "
            "AND COALESCE(NULLIF(album_key, ''), album, '')=? "
            "ORDER BY COALESCE(disc_number, 1), COALESCE(track_number, 999), title",
            (album_key,),
        ).fetchall()
        keys = ["track_id", "filepath", "title", "artist", "album", "duration",
                "track_number", "disc_number", "track_uid", "album_key", "year", "genre"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def multi_disc(self, album_key: str) -> bool:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT COALESCE(disc_number, 1)) "
            "FROM media_items WHERE deleted_at IS NULL "
            "AND COALESCE(NULLIF(album_key, ''), album, '')=?",
            (album_key,),
        ).fetchone()
        return (row[0] if row else 0) > 1

    def sort(self, sort: str = "year", asc: bool = False,
             offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.get_page(offset=offset, limit=limit, sort=sort, asc=asc)

    def filter(self, year: int | None = None, genre: str | None = None,
               artist: str | None = None) -> list[dict[str, Any]]:
        clauses = [
            "m.deleted_at IS NULL",
            "COALESCE(m.album, '') != ''",
        ]
        params = []
        if year is not None:
            clauses.append("m.year=?")
            params.append(year)
        if genre:
            clauses.append("m.genre=?")
            params.append(genre)
        if artist:
            clauses.append(
                "(COALESCE(NULLIF(m.albumartist,''), m.artist, '')=? OR m.artist=?)")
            params.extend([artist, artist])
        where = " AND ".join(clauses)
        rows = self._conn().execute(
            f"SELECT {_ALBUM_SELECT} "
            "FROM media_items m "
            f"WHERE {where} "
            "GROUP BY album_key",
            params,
        ).fetchall()
        keys = ["album_key", "album_title", "album_artist", "year",
                "track_count", "total_duration", "genre", "disc_count"]
        return [dict(zip(keys, r, strict=False)) for r in rows]
