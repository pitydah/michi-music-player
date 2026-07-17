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

    def by_field(self, field: str, value: str = "", limit: int = 30) -> list[dict]:
        """Obtiene canciones por campo (artist, genre, album)."""
        if not self._db:
            return []
        try:
            valid_fields = {"artist", "genre", "album", "albumartist"}
            if field not in valid_fields:
                field = "artist"
            if value:
                sql = (
                    f"SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    f"FROM media_items m WHERE m.deleted_at IS NULL AND m.{field} = ? "
                    f"ORDER BY m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [value, limit]).fetchall()
            else:
                sql = (
                    f"SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    f"FROM media_items m WHERE m.deleted_at IS NULL AND m.{field} IS NOT NULL AND m.{field} != '' "
                    f"ORDER BY m.{field}, m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [limit]).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0}
                for r in rows
            ]
        except Exception as e:
            logger.debug("by_field failed: %s", e)
            return []

    def by_decade(self, decade: int = 0, limit: int = 30) -> list[dict]:
        """Obtiene canciones por década. Si decade=0, devuelve década aleatoria."""
        if not self._db:
            return []
        try:
            if decade > 0:
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    "FROM media_items m WHERE m.deleted_at IS NULL "
                    "AND m.year >= ? AND m.year < ? "
                    "ORDER BY m.year DESC, m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [decade, decade + 10, limit]).fetchall()
            else:
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration, "
                    "(m.year / 10 * 10) as decade "
                    "FROM media_items m WHERE m.deleted_at IS NULL AND m.year > 0 "
                    "ORDER BY RANDOM() LIMIT 1"
                )
                row = self._db.conn.execute(sql).fetchone()
                if not row:
                    return []
                d = row[6] or 1980
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    "FROM media_items m WHERE m.deleted_at IS NULL "
                    "AND m.year >= ? AND m.year < ? "
                    "ORDER BY m.year DESC, m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [d, d + 10, limit]).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0}
                for r in rows
            ]
        except Exception as e:
            logger.debug("by_decade failed: %s", e)
            return []

    def by_year(self, year: int = 0, limit: int = 30) -> list[dict]:
        """Obtiene canciones por año específico. Si year=0, devuelve año aleatorio."""
        if not self._db:
            return []
        try:
            if year > 0:
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    "FROM media_items m WHERE m.deleted_at IS NULL AND m.year = ? "
                    "ORDER BY m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [year, limit]).fetchall()
            else:
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration, m.year "
                    "FROM media_items m WHERE m.deleted_at IS NULL AND m.year > 0 "
                    "ORDER BY RANDOM() LIMIT 1"
                )
                row = self._db.conn.execute(sql).fetchone()
                if not row:
                    return []
                y = row[6] or 2000
                sql = (
                    "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                    "FROM media_items m WHERE m.deleted_at IS NULL AND m.year = ? "
                    "ORDER BY m.created_at DESC"
                )
                rows = self._db.conn.execute(sql, [y, limit]).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0}
                for r in rows
            ]
        except Exception as e:
            logger.debug("by_year failed: %s", e)
            return []

    def high_quality(self, min_bitrate: int = 320, limit: int = 30) -> list[dict]:
        """Obtiene canciones de alta calidad (bitrate >= min_bitrate)."""
        if not self._db:
            return []
        try:
            sql = (
                "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                "FROM media_items m WHERE m.deleted_at IS NULL "
                "AND m.bitrate >= ? "
                "ORDER BY m.bitrate DESC, m.created_at DESC"
            )
            rows = self._db.conn.execute(sql, [min_bitrate, limit]).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0,
                 "bitrate": getattr(r, 'bitrate', 0) if hasattr(r, 'bitrate') else (r[6] if len(r) > 6 else 0)}
                for r in rows
            ]
        except Exception as e:
            logger.debug("high_quality failed: %s", e)
            return []

    def rediscovery(self, limit: int = 30) -> list[dict]:
        """Obtiene canciones antiguas que no se escuchan hace tiempo."""
        if not self._db:
            return []
        try:
            import time
            six_months_ago = int(time.time()) - (180 * 24 * 60 * 60)
            sql = (
                "SELECT m.id, m.title, m.artist, m.album, m.album_key, m.duration "
                "FROM media_items m WHERE m.deleted_at IS NULL "
                "AND (m.last_played IS NULL OR m.last_played < ?) "
                "AND m.play_count > 0 "
                "ORDER BY m.last_played ASC, m.created_at DESC"
            )
            rows = self._db.conn.execute(sql, [six_months_ago, limit]).fetchall()
            return [
                {"track_id": r[0], "title": r[1] or "", "artist": r[2] or "",
                 "album": r[3] or "", "album_key": r[4] or "", "duration": r[5] or 0}
                for r in rows
            ]
        except Exception as e:
            logger.debug("rediscovery failed: %s", e)
            return []
