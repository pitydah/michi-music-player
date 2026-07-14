from __future__ import annotations

import sqlite3
from typing import Any


class LibraryStatsRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def total_tracks(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL",
        ).fetchone()
        return row[0] if row else 0

    def total_albums(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(album_key, ''), album, '')) "
            "FROM media_items WHERE deleted_at IS NULL AND COALESCE(album,'')!=''",
        ).fetchone()
        return row[0] if row else 0

    def total_artists(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(albumartist,''), artist, '')) "
            "FROM media_items WHERE deleted_at IS NULL AND COALESCE(artist,'')!=''",
        ).fetchone()
        return row[0] if row else 0

    def total_duration(self) -> float:
        row = self._conn().execute(
            "SELECT COALESCE(SUM(duration), 0) FROM media_items WHERE deleted_at IS NULL",
        ).fetchone()
        return float(row[0]) if row else 0.0

    def total_size(self) -> int:
        row = self._conn().execute(
            "SELECT COALESCE(SUM(size), 0) FROM media_items WHERE deleted_at IS NULL",
        ).fetchone()
        return row[0] if row else 0

    def by_format(self) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT LOWER(COALESCE(ext, '')) as format, "
            "COUNT(*) as count, "
            "COALESCE(SUM(duration), 0) as total_duration, "
            "COALESCE(SUM(size), 0) as total_size "
            "FROM media_items WHERE deleted_at IS NULL "
            "GROUP BY format ORDER BY count DESC",
        ).fetchall()
        keys = ["format", "count", "total_duration", "total_size"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def by_year(self) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT COALESCE(year, 0) as year, "
            "COUNT(*) as count, "
            "COALESCE(SUM(duration), 0) as total_duration "
            "FROM media_items WHERE deleted_at IS NULL AND year > 0 "
            "GROUP BY year ORDER BY year DESC",
        ).fetchall()
        keys = ["year", "count", "total_duration"]
        return [dict(zip(keys, r, strict=False)) for r in rows]
