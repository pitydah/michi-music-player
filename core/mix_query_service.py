"""Read-only query backend for generated and rule-based mixes.

The service owns the SQL required by :class:`core.mix_service.MixService` and
returns queue-ready track dictionaries. It deliberately uses the shared
``LibraryConnectionFactory`` when available so mix generation does not bypass
Michi's canonical read-only connection boundary.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Iterable, Mapping

logger = logging.getLogger("michi.mix_query")

_ALLOWED_FIELDS = {
    "artist": "COALESCE(NULLIF(m.albumartist, ''), m.artist, '')",
    "albumartist": "COALESCE(NULLIF(m.albumartist, ''), m.artist, '')",
    "album": "COALESCE(m.album, '')",
    "genre": "COALESCE(m.genre, '')",
}

_LOSSLESS_EXTENSIONS = (
    "flac", "alac", "ape", "wav", "aiff", "aif", "wv", "dsf", "dff"
)


class MixQueryError(RuntimeError):
    """Raised when a mix query cannot be executed safely."""

    def __init__(self, code: str, operation: str, detail: str = "") -> None:
        self.code = code
        self.operation = operation
        self.detail = detail
        super().__init__(detail or code)


class MixQueryService:
    """Provide parameterized, queue-ready library queries for mix generation."""

    def __init__(
        self,
        db: Any | None = None,
        connection_factory: Any | None = None,
    ) -> None:
        self._db = db
        self._connection_factory = connection_factory
        self._last_error = ""

    @property
    def available(self) -> bool:
        return self._connection_factory is not None or self._db is not None

    @property
    def last_error(self) -> str:
        return self._last_error

    def _connection(self) -> sqlite3.Connection:
        if self._connection_factory is not None:
            getter = getattr(self._connection_factory, "get_connection", None)
            if callable(getter):
                return getter()
        connection = getattr(self._db, "conn", None)
        if connection is not None:
            return connection
        raise MixQueryError(
            "NO_DATABASE", "connection", "Base de datos no disponible"
        )

    @staticmethod
    def _bounded_limit(limit: int, maximum: int = 500) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError):
            value = 30
        return max(1, min(maximum, value))

    @staticmethod
    def _row_value(
        row: Any, index: int, key: str, default: Any = None
    ) -> Any:
        if isinstance(row, Mapping):
            return row.get(key, default)
        try:
            return row[index]
        except (IndexError, KeyError, TypeError):
            return default

    @classmethod
    def _to_track(cls, row: Any) -> dict[str, Any]:
        track_id = int(cls._row_value(row, 0, "id", 0) or 0)
        filepath = str(cls._row_value(row, 1, "filepath", "") or "")
        ext = str(cls._row_value(row, 7, "ext", "") or "").lstrip(".").lower()
        return {
            "id": track_id,
            "track_id": track_id,
            "filepath": filepath,
            "path": filepath,
            "title": str(cls._row_value(row, 2, "title", "") or ""),
            "artist": str(cls._row_value(row, 3, "artist", "") or ""),
            "album": str(cls._row_value(row, 4, "album", "") or ""),
            "album_key": str(cls._row_value(row, 5, "album_key", "") or ""),
            "duration": float(cls._row_value(row, 6, "duration", 0) or 0),
            "format": ext,
            "ext": ext,
            "year": int(cls._row_value(row, 8, "year", 0) or 0),
            "genre": str(cls._row_value(row, 9, "genre", "") or ""),
            "bitrate": int(cls._row_value(row, 10, "bitrate", 0) or 0),
            "sample_rate": int(
                cls._row_value(row, 11, "sample_rate", 0) or 0
            ),
            "bit_depth": int(cls._row_value(row, 12, "bit_depth", 0) or 0),
            "channels": int(cls._row_value(row, 13, "channels", 0) or 0),
            "track_uid": str(cls._row_value(row, 14, "track_uid", "") or ""),
        }

    def _execute(
        self,
        operation: str,
        *,
        where: str = "",
        params: Iterable[Any] = (),
        order_by: str = "LOWER(COALESCE(m.title, '')) ASC, m.id ASC",
        limit: int = 30,
        joins: str = "",
    ) -> list[dict[str, Any]]:
        bounded = self._bounded_limit(limit)
        sql = (
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.album_key, "
            "m.duration, m.ext, m.year, m.genre, m.bitrate, m.sample_rate, "
            "m.bit_depth, m.channels, m.track_uid "
            "FROM media_items m "
            f"{joins} "
            "WHERE m.deleted_at IS NULL "
            f"{where} ORDER BY {order_by} LIMIT ?"
        )
        values = list(params)
        values.append(bounded)
        try:
            rows = self._connection().execute(sql, values).fetchall()
        except MixQueryError:
            raise
        except (sqlite3.DatabaseError, AttributeError, TypeError) as exc:
            self._last_error = f"{operation}: {exc}"
            logger.warning(
                "Mix query '%s' failed: %s", operation, exc, exc_info=True
            )
            raise MixQueryError("QUERY_FAILED", operation, str(exc)) from exc
        self._last_error = ""
        return [self._to_track(row) for row in rows]

    def fetch_tracks(
        self, sql: str, params: list, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Compatibility entry point for allowlisted SELECT statements.

        New callers should prefer the named query methods below. Arbitrary
        mutation statements and multi-statement SQL are rejected.
        """
        normalized = " ".join(str(sql or "").strip().split()).lower()
        if not normalized.startswith("select ") or ";" in normalized:
            raise MixQueryError(
                "UNSAFE_QUERY",
                "fetch_tracks",
                "Solo se permiten SELECT simples",
            )
        bounded = self._bounded_limit(limit)
        try:
            rows = self._connection().execute(
                f"{sql} LIMIT ?", [*params, bounded]
            ).fetchall()
        except (sqlite3.DatabaseError, AttributeError, TypeError) as exc:
            self._last_error = f"fetch_tracks: {exc}"
            logger.warning(
                "Compatibility mix query failed: %s", exc, exc_info=True
            )
            raise MixQueryError("QUERY_FAILED", "fetch_tracks", str(exc)) from exc
        self._last_error = ""
        return [self._to_track(row) for row in rows]

    def favorites(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._execute(
            "favorites",
            where=(
                "AND EXISTS (SELECT 1 FROM favorites f WHERE "
                "f.track_id = m.filepath OR f.track_id = CAST(m.id AS TEXT) "
                "OR (NULLIF(m.track_uid, '') IS NOT NULL "
                "AND f.track_id = m.track_uid))"
            ),
            order_by=(
                "COALESCE((SELECT MAX(f.added_at) FROM favorites f WHERE "
                "f.track_id = m.filepath OR f.track_id = CAST(m.id AS TEXT) "
                "OR f.track_id = m.track_uid), 0) DESC, m.id DESC"
            ),
            limit=limit,
        )

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._execute(
            "recent",
            where="AND COALESCE(m.last_played, 0) > 0",
            order_by="COALESCE(m.last_played, 0) DESC, m.id DESC",
            limit=limit,
        )

    def most_played(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._execute(
            "most_played",
            where="AND COALESCE(m.play_count, 0) > 0",
            order_by=(
                "COALESCE(m.play_count, 0) DESC, "
                "COALESCE(m.last_played, 0) DESC, m.id ASC"
            ),
            limit=limit,
        )

    def unplayed(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._execute(
            "unplayed",
            where="AND COALESCE(m.play_count, 0) = 0",
            order_by=(
                "COALESCE(m.created_at, m.date_added, 0) DESC, m.id DESC"
            ),
            limit=limit,
        )

    def genre(self, genre: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.by_field("genre", value=genre, limit=limit)

    def _representative_value(self, field: str) -> str:
        expression = _ALLOWED_FIELDS[field]
        sql = (
            f"SELECT {expression} AS value, COUNT(*) AS total "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            f"AND {expression} != '' GROUP BY value "
            "ORDER BY total DESC, LOWER(value) ASC LIMIT 1"
        )
        try:
            row = self._connection().execute(sql).fetchone()
        except (sqlite3.DatabaseError, AttributeError, TypeError) as exc:
            raise MixQueryError(
                "QUERY_FAILED", "representative_value", str(exc)
            ) from exc
        return (
            str(self._row_value(row, 0, "value", "") or "") if row else ""
        )

    def by_field(
        self, field: str, value: str = "", limit: int = 30
    ) -> list[dict[str, Any]]:
        field_key = str(field or "").strip().lower()
        if field_key not in _ALLOWED_FIELDS:
            raise MixQueryError("INVALID_FIELD", "by_field", field_key)
        selected = str(value or "").strip() or self._representative_value(field_key)
        if not selected:
            return []
        expression = _ALLOWED_FIELDS[field_key]
        return self._execute(
            f"by_{field_key}",
            where=f"AND {expression} = ? COLLATE NOCASE",
            params=[selected],
            order_by=(
                "COALESCE(m.disc_number, 0) ASC, "
                "COALESCE(m.track_number, 0) ASC, m.id ASC"
            ),
            limit=limit,
        )

    def by_album(
        self, album: str = "", limit: int = 30
    ) -> list[dict[str, Any]]:
        return self.by_field("album", value=album, limit=limit)

    def _representative_number(self, expression: str, operation: str) -> int:
        sql = (
            f"SELECT {expression} AS value, COUNT(*) AS total "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            f"AND {expression} > 0 GROUP BY value "
            "ORDER BY total DESC, value DESC LIMIT 1"
        )
        try:
            row = self._connection().execute(sql).fetchone()
        except (sqlite3.DatabaseError, AttributeError, TypeError) as exc:
            raise MixQueryError("QUERY_FAILED", operation, str(exc)) from exc
        return int(self._row_value(row, 0, "value", 0) or 0) if row else 0

    def by_decade(
        self, decade: int = 0, limit: int = 30
    ) -> list[dict[str, Any]]:
        try:
            selected = int(decade or 0)
        except (TypeError, ValueError):
            selected = 0
        selected = (selected // 10) * 10 if selected > 0 else 0
        if selected <= 0:
            selected = self._representative_number(
                "(CAST(m.year AS INTEGER) / 10) * 10", "by_decade"
            )
        if selected <= 0:
            return []
        return self._execute(
            "by_decade",
            where=(
                "AND CAST(m.year AS INTEGER) >= ? "
                "AND CAST(m.year AS INTEGER) < ?"
            ),
            params=[selected, selected + 10],
            order_by=(
                "CAST(m.year AS INTEGER) ASC, "
                "LOWER(COALESCE(m.album, '')) ASC, "
                "COALESCE(m.track_number, 0) ASC"
            ),
            limit=limit,
        )

    def by_year(
        self, year: int = 0, limit: int = 30
    ) -> list[dict[str, Any]]:
        try:
            selected = int(year or 0)
        except (TypeError, ValueError):
            selected = 0
        if selected <= 0:
            selected = self._representative_number(
                "CAST(m.year AS INTEGER)", "by_year"
            )
        if selected <= 0:
            return []
        return self._execute(
            "by_year",
            where="AND CAST(m.year AS INTEGER) = ?",
            params=[selected],
            order_by=(
                "LOWER(COALESCE(m.album, '')) ASC, "
                "COALESCE(m.disc_number, 0) ASC, "
                "COALESCE(m.track_number, 0) ASC"
            ),
            limit=limit,
        )

    def high_quality(
        self,
        min_bitrate: int = 320,
        limit: int = 30,
        *,
        lossless: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            bitrate = max(0, int(min_bitrate or 0))
        except (TypeError, ValueError):
            bitrate = 320
        if lossless:
            placeholders = ", ".join("?" for _ in _LOSSLESS_EXTENSIONS)
            return self._execute(
                "high_quality_lossless",
                where=(
                    "AND LOWER(LTRIM(COALESCE(m.ext, ''), '.')) "
                    f"IN ({placeholders})"
                ),
                params=list(_LOSSLESS_EXTENSIONS),
                order_by=(
                    "COALESCE(m.bit_depth, 0) DESC, "
                    "COALESCE(m.sample_rate, 0) DESC, m.id ASC"
                ),
                limit=limit,
            )
        return self._execute(
            "high_quality",
            where="AND COALESCE(m.bitrate, 0) >= ?",
            params=[bitrate],
            order_by=(
                "COALESCE(m.bitrate, 0) DESC, "
                "COALESCE(m.sample_rate, 0) DESC, m.id ASC"
            ),
            limit=limit,
        )

    def rediscovery(
        self, limit: int = 30, older_than_days: int = 180
    ) -> list[dict[str, Any]]:
        try:
            days = max(1, int(older_than_days))
        except (TypeError, ValueError):
            days = 180
        cutoff = int(time.time()) - days * 24 * 60 * 60
        return self._execute(
            "rediscovery",
            where=(
                "AND COALESCE(m.play_count, 0) > 0 "
                "AND (m.last_played IS NULL OR COALESCE(m.last_played, 0) < ?)"
            ),
            params=[cutoff],
            order_by=(
                "COALESCE(m.last_played, 0) ASC, "
                "COALESCE(m.play_count, 0) DESC, m.id ASC"
            ),
            limit=limit,
        )

    def custom(
        self,
        filters: Mapping[str, Any] | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Generate a mix from the filters exposed by MixGeneratorPage.qml."""
        data = dict(filters or {})
        clauses: list[str] = []
        params: list[Any] = []

        artist = str(
            data.get("seed_artist") or data.get("artist") or ""
        ).strip()
        album = str(data.get("album") or "").strip()
        genre = str(data.get("genre") or "").strip()
        seed = str(data.get("seed") or "").strip()
        if seed and not any((artist, album, genre)):
            clauses.append(
                "AND (m.title LIKE ? COLLATE NOCASE "
                "OR m.artist LIKE ? COLLATE NOCASE "
                "OR m.album LIKE ? COLLATE NOCASE "
                "OR m.genre LIKE ? COLLATE NOCASE)"
            )
            pattern = f"%{seed}%"
            params.extend([pattern, pattern, pattern, pattern])
        if artist:
            clauses.append(
                "AND COALESCE(NULLIF(m.albumartist, ''), m.artist, '') "
                "= ? COLLATE NOCASE"
            )
            params.append(artist)
        if album:
            clauses.append("AND COALESCE(m.album, '') = ? COLLATE NOCASE")
            params.append(album)
        if genre:
            clauses.append("AND COALESCE(m.genre, '') = ? COLLATE NOCASE")
            params.append(genre)

        for key, operator in (("year_from", ">="), ("year_to", "<=")):
            raw = data.get(key)
            if raw not in (None, "", 0, "0"):
                try:
                    year = int(raw)
                except (TypeError, ValueError):
                    raise MixQueryError(
                        "INVALID_FILTER", "custom", key
                    ) from None
                clauses.append(f"AND CAST(m.year AS INTEGER) {operator} ?")
                params.append(year)

        quality = str(data.get("quality") or "").strip().lower()
        if quality == "lossless":
            placeholders = ", ".join("?" for _ in _LOSSLESS_EXTENSIONS)
            clauses.append(
                "AND LOWER(LTRIM(COALESCE(m.ext, ''), '.')) "
                f"IN ({placeholders})"
            )
            params.extend(_LOSSLESS_EXTENSIONS)
        elif quality:
            try:
                minimum = int(quality)
            except ValueError:
                raise MixQueryError(
                    "INVALID_FILTER", "custom", "quality"
                ) from None
            clauses.append("AND COALESCE(m.bitrate, 0) >= ?")
            params.append(minimum)

        if bool(data.get("avoid_recent")):
            recent_cutoff = int(time.time()) - 7 * 24 * 60 * 60
            clauses.append(
                "AND (m.last_played IS NULL OR COALESCE(m.last_played, 0) < ?)"
            )
            params.append(recent_cutoff)

        exclusions = data.get("exclusions") or []
        if isinstance(exclusions, str):
            exclusions = [
                part.strip() for part in exclusions.split(",") if part.strip()
            ]
        for exclusion in exclusions:
            pattern = f"%{str(exclusion).strip()}%"
            clauses.append(
                "AND NOT (m.artist LIKE ? COLLATE NOCASE "
                "OR m.album LIKE ? COLLATE NOCASE "
                "OR m.genre LIKE ? COLLATE NOCASE)"
            )
            params.extend([pattern, pattern, pattern])

        requested = data.get("limit", limit)
        return self._execute(
            "custom",
            where=" ".join(clauses),
            params=params,
            order_by="RANDOM()",
            limit=self._bounded_limit(requested),
        )
