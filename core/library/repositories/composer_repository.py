from __future__ import annotations

import sqlite3
from typing import Any


class ComposerRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def get_all(self) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT COALESCE(composer, '') as name, "
            "COUNT(*) as track_count, "
            "COUNT(DISTINCT COALESCE(album, '')) as album_count "
            "FROM media_items "
            "WHERE deleted_at IS NULL AND COALESCE(composer, '') != '' "
            "GROUP BY composer ORDER BY track_count DESC",
        ).fetchall()
        keys = ["name", "track_count", "album_count"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def get_page(self, offset: int = 0, limit: int = 100,
                 asc: bool = True) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT COALESCE(composer, '') as name, "
            "COUNT(*) as track_count, "
            "COUNT(DISTINCT COALESCE(album, '')) as album_count "
            "FROM media_items "
            "WHERE deleted_at IS NULL AND COALESCE(composer, '') != '' "
            "GROUP BY composer "
            "ORDER BY LOWER(name) ASC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        keys = ["name", "track_count", "album_count"]
        return [dict(zip(keys, r, strict=False)) for r in rows]

    def count(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT composer) FROM media_items "
            "WHERE deleted_at IS NULL AND COALESCE(composer, '') != ''",
        ).fetchone()
        return row[0] if row else 0
