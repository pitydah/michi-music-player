"""SQL-backed queries used by the Mix domain.

All public selectors apply their own bounded ``LIMIT`` and return the same
track dictionary shape.  Query failures are logged and converted to an empty
result so the QML bridge can display an honest empty/error state without
crashing the application.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Sequence

logger = logging.getLogger("michi.mix_query")


class MixQueryService:
    def __init__(self, db=None):
        self._db = db

    @staticmethod
    def _bounded_limit(limit: int, default: int = 50, maximum: int = 500) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError):
            value = default
        return max(1, min(value, maximum))

    def _execute(self, sql: str, params: Sequence | None = None):
        if not self._db or not getattr(self._db, "conn", None):
            return []
        return self._db.conn.execute(sql, list(params or [])).fetchall()

    @staticmethod
    def _track_from_row(row) -> dict:
        return {
            "track_id": row[0],
            "title": row[1] or "",
            "artist": row[2] or "",
            "album": row[3] or "",
            "album_key": row[4] or "",
            "duration": row[5] or 0,
        }

    def fetch_tracks(self, sql: str, params: Sequence | None = None, limit: int = 50) -> list[dict]:
        """Execute a track query and append exactly one SQL limit parameter.

        Callers must provide a query without a trailing ``LIMIT`` clause.  This
        centralises bound checking and prevents the parameter-count mismatch
        that previously made artist, genre, decade, year and quality mixes
        silently return no songs.
        """
        if not self._db:
            return []
        bounded = self._bounded_limit(limit)
        try:
            rows = self._execute(f"{sql.rstrip()} LIMIT ?", [*(params or []), bounded])
            return [self._track_from_row(row) for row in rows]
        except Exception as exc:
            logger.warning("mix query failed: %s", exc, exc_info=True)
            return []

    def favorites(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m JOIN favorites f ON m.filepath = f.track_id "
            "WHERE m.deleted_at IS NULL ORDER BY f.added_at DESC",
            limit=limit,
        )

    def recent(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.last_played > 0 "
            "ORDER BY m.last_played DESC",
            limit=limit,
        )

    def most_played(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.play_count > 0 "
            "ORDER BY m.play_count DESC",
            limit=limit,
        )

    def unplayed(self, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND "
            "(m.play_count IS NULL OR m.play_count = 0) "
            "ORDER BY m.created_at DESC",
            limit=limit,
        )

    def genre(self, genre: str, limit: int = 50) -> list[dict]:
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.genre = ? "
            "ORDER BY m.created_at DESC",
            [genre],
            limit,
        )

    def by_field(self, field: str, value: str = "", limit: int = 30) -> list[dict]:
        """Return tracks grouped or filtered by an allow-listed metadata field."""
        valid_fields = {"artist", "genre", "album", "albumartist"}
        safe_field = field if field in valid_fields else "artist"
        base = (
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL "
        )
        if value:
            return self.fetch_tracks(
                base + f"AND m.{safe_field} = ? ORDER BY m.created_at DESC",
                [value],
                limit,
            )
        return self.fetch_tracks(
            base
            + f"AND m.{safe_field} IS NOT NULL AND m.{safe_field} != '' "
            + f"ORDER BY m.{safe_field}, m.created_at DESC",
            limit=limit,
        )

    def _random_year_bucket(self, expression: str) -> int | None:
        if not self._db:
            return None
        try:
            row = self._db.conn.execute(
                "SELECT " + expression + " AS bucket FROM media_items m "
                "WHERE m.deleted_at IS NULL AND m.year > 0 "
                "GROUP BY bucket ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
            return int(row[0]) if row and row[0] is not None else None
        except Exception as exc:
            logger.warning("random mix bucket failed: %s", exc, exc_info=True)
            return None

    def by_decade(self, decade: int = 0, limit: int = 30) -> list[dict]:
        try:
            selected = int(decade or 0)
        except (TypeError, ValueError):
            selected = 0
        if selected <= 0:
            selected = self._random_year_bucket("CAST(m.year / 10 AS INTEGER) * 10") or 0
        if selected <= 0:
            return []
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            "AND m.year >= ? AND m.year < ? "
            "ORDER BY m.year DESC, m.created_at DESC",
            [selected, selected + 10],
            limit,
        )

    def by_year(self, year: int = 0, limit: int = 30) -> list[dict]:
        try:
            selected = int(year or 0)
        except (TypeError, ValueError):
            selected = 0
        if selected <= 0:
            selected = self._random_year_bucket("m.year") or 0
        if selected <= 0:
            return []
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL AND m.year = ? "
            "ORDER BY m.created_at DESC",
            [selected],
            limit,
        )

    def high_quality(self, min_bitrate: int = 320, limit: int = 30) -> list[dict]:
        if not self._db:
            return []
        bounded = self._bounded_limit(limit, default=30)
        try:
            bitrate = max(0, int(min_bitrate))
            rows = self._execute(
                "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration, m.bitrate "
                "FROM media_items m WHERE m.deleted_at IS NULL AND m.bitrate >= ? "
                "ORDER BY m.bitrate DESC, m.created_at DESC LIMIT ?",
                [bitrate, bounded],
            )
            results = []
            for row in rows:
                item = self._track_from_row(row)
                item["bitrate"] = row[6] or 0
                results.append(item)
            return results
        except Exception as exc:
            logger.warning("high-quality mix failed: %s", exc, exc_info=True)
            return []

    def rediscovery(self, limit: int = 30) -> list[dict]:
        six_months_ago = int(time.time()) - (180 * 24 * 60 * 60)
        return self.fetch_tracks(
            "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            "AND (m.last_played IS NULL OR m.last_played < ?) "
            "AND m.play_count > 0 "
            "ORDER BY m.last_played ASC, m.created_at DESC",
            [six_months_ago],
            limit,
        )
