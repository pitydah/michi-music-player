from __future__ import annotations

import datetime
import sqlite3
from typing import Callable

from core.radio.models import (
    Station, StationId, StationCreateRequest, StationUpdateRequest,
    PaginatedResult,
)
from core.radio.url_utils import urls_are_equivalent
from infrastructure.radio.schema import create_schema, migrate

_COLS = [
    "id", "name", "stream_url", "homepage_url", "favicon_url",
    "genre", "country", "language", "codec", "bitrate",
    "favorite", "created_at", "updated_at", "last_played_at",
    "play_count", "last_probe_status", "last_probe_at",
]
_COLS_STR = ", ".join(_COLS)
_PLACEHOLDERS = ", ".join("?" for _ in _COLS)
_UPDATABLE_COLS = [
    "name", "stream_url", "homepage_url", "favicon_url",
    "genre", "country", "language", "codec", "bitrate",
    "favorite",
]


def _row_to_station(row: tuple) -> Station:
    data = dict(zip(_COLS, row, strict=True))
    if isinstance(data.get("favorite"), int):
        data["favorite"] = bool(data["favorite"])
    return Station(**data)


_SAFE_SORT_COLS = frozenset({
    "name", "created_at", "updated_at", "bitrate",
    "play_count", "favorite", "country", "genre",
})


class SqliteStationRepository:
    def __init__(self, db_path: str, clock: Callable[[], str] | None = None):
        self._db_path = db_path
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self):
        conn = self._conn()
        try:
            create_schema(conn)
            migrate(conn)
            conn.commit()
        finally:
            conn.close()

    def add(self, req: StationCreateRequest) -> Station:
        now = self._clock()
        conn = self._conn()
        try:
            existing = self._find_by_url_as_station(conn, req.stream_url)
            if existing:
                station = self._update_row(conn, existing.id, req, now)
                conn.commit()
                return station
            cur = conn.execute(
                "INSERT INTO radio_stations "
                "(name, stream_url, homepage_url, favicon_url, genre, country, language, codec, bitrate, "
                "favorite, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (req.name, req.stream_url, req.homepage_url, req.favicon_url,
                 req.genre, req.country, req.language, req.codec, req.bitrate,
                 now, now),
            )
            station_id = cur.lastrowid
            conn.commit()
            return self.get(station_id)
        finally:
            conn.close()

    def get(self, station_id: StationId) -> Station | None:
        conn = self._conn()
        try:
            row = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE id = ? AND deleted = 0",
                (station_id,),
            ).fetchone()
            return _row_to_station(row) if row else None
        finally:
            conn.close()

    def update(self, station_id: StationId, req: StationUpdateRequest) -> Station | None:
        now = self._clock()
        conn = self._conn()
        try:
            existing = conn.execute("SELECT * FROM radio_stations WHERE id = ? AND deleted = 0", (station_id,)).fetchone()
            if not existing:
                return None
            station = self._update_row(conn, station_id, req, now)
            conn.commit()
            return station
        finally:
            conn.close()

    def _update_row(self, conn: sqlite3.Connection, station_id: StationId,
                    req: StationCreateRequest | StationUpdateRequest, now: str) -> Station:
        vals = {}
        for col in _UPDATABLE_COLS:
            v = getattr(req, col, None)
            if v is not None:
                vals[col] = v
        if vals:
            vals["updated_at"] = now
            sets = ", ".join(f"{k} = ?" for k in vals)
            conn.execute(
                f"UPDATE radio_stations SET {sets} WHERE id = ?",
                [*list(vals.values()), station_id],
            )
        row = conn.execute(
            f"SELECT {_COLS_STR} FROM radio_stations WHERE id = ?",
            (station_id,),
        ).fetchone()
        return _row_to_station(row) if row else None

    def delete(self, station_id: StationId) -> bool:
        conn = self._conn()
        try:
            row = conn.execute("SELECT id FROM radio_stations WHERE id = ? AND deleted = 0", (station_id,)).fetchone()
            if not row:
                return False
            conn.execute("UPDATE radio_stations SET deleted = 1, updated_at = ? WHERE id = ?",
                         (self._clock(), station_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def list_all(self, page: int = 1, page_size: int = 50, sort_by: str = "name",
                 sort_dir: str = "asc") -> PaginatedResult:
        if sort_by not in _SAFE_SORT_COLS:
            sort_by = "name"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "asc"
        offset = (page - 1) * page_size
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM radio_stations WHERE deleted = 0").fetchone()[0]
            rows = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0 ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            return PaginatedResult(
                items=[_row_to_station(r) for r in rows],
                total=total, page=page, page_size=page_size,
                pages=max(1, (total + page_size - 1) // page_size),
            )
        finally:
            conn.close()

    def search(self, query: str, page: int = 1, page_size: int = 50) -> PaginatedResult:
        offset = (page - 1) * page_size
        pattern = f"%{query}%"
        conn = self._conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) FROM radio_stations WHERE deleted = 0 AND "
                "(name LIKE ? OR genre LIKE ? OR country LIKE ? OR language LIKE ? OR stream_url LIKE ?)",
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0 AND "
                "(name LIKE ? OR genre LIKE ? OR country LIKE ? OR language LIKE ? OR stream_url LIKE ?) "
                "ORDER BY favorite DESC, name ASC LIMIT ? OFFSET ?",
                (pattern, pattern, pattern, pattern, pattern, page_size, offset),
            ).fetchall()
            return PaginatedResult(
                items=[_row_to_station(r) for r in rows],
                total=total, page=page, page_size=page_size,
                pages=max(1, (total + page_size - 1) // page_size),
            )
        finally:
            conn.close()

    def count(self) -> int:
        conn = self._conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM radio_stations WHERE deleted = 0").fetchone()[0]
        finally:
            conn.close()

    def set_favorite(self, station_id: StationId, favorite: bool) -> bool:
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE radio_stations SET favorite = ?, updated_at = ? WHERE id = ? AND deleted = 0",
                (1 if favorite else 0, self._clock(), station_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def list_favorites(self, page: int = 1, page_size: int = 50) -> PaginatedResult:
        return self._list_where("favorite = 1", page, page_size)

    def find_by_url(self, url: str) -> Station | None:
        conn = self._conn()
        try:
            return self._find_by_url_as_station(conn, url)
        finally:
            conn.close()

    def _find_by_url(self, conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
        rows = conn.execute(
            f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0"
        ).fetchall()
        for row in rows:
            if urls_are_equivalent(row["stream_url"], url):
                return row
        return None

    def _find_by_url_as_station(self, conn: sqlite3.Connection, url: str) -> Station | None:
        row = self._find_by_url(conn, url)
        return _row_to_station(row) if row else None

    def mark_played(self, station_id: StationId):
        now = self._clock()
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE radio_stations SET last_played_at = ?, play_count = play_count + 1, updated_at = ? WHERE id = ?",
                (now, now, station_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_recent(self, limit: int = 20) -> list[Station]:
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0 AND last_played_at != '' "
                "ORDER BY last_played_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_row_to_station(r) for r in rows]
        finally:
            conn.close()

    def update_probe(self, station_id: StationId, status: str, probe_at: str):
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE radio_stations SET last_probe_status = ?, last_probe_at = ? WHERE id = ?",
                (status, probe_at, station_id),
            )
            conn.commit()
        finally:
            conn.close()

    def bulk_add(self, stations: list[StationCreateRequest], mode: str = "best_effort") -> int:
        count = 0
        conn = self._conn()
        try:
            for req in stations:
                try:
                    existing = self._find_by_url(conn, req.stream_url)
                    if existing:
                        if mode == "all_or_nothing":
                            raise ValueError(f"Duplicate: {req.stream_url}")
                        continue
                    now = self._clock()
                    conn.execute(
                        "INSERT INTO radio_stations "
                        "(name, stream_url, homepage_url, favicon_url, genre, country, language, codec, bitrate, "
                        "favorite, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                        (req.name, req.stream_url, req.homepage_url, req.favicon_url,
                         req.genre, req.country, req.language, req.codec, req.bitrate,
                         now, now),
                    )
                    count += 1
                except Exception:
                    if mode == "all_or_nothing":
                        conn.rollback()
                        return 0
            conn.commit()
        finally:
            conn.close()
        return count

    def get_all_for_export(self) -> list[Station]:
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0 ORDER BY name ASC"
            ).fetchall()
            return [_row_to_station(r) for r in rows]
        finally:
            conn.close()

    def _list_where(self, where_clause: str, page: int, page_size: int) -> PaginatedResult:
        offset = (page - 1) * page_size
        conn = self._conn()
        try:
            total = conn.execute(f"SELECT COUNT(*) FROM radio_stations WHERE deleted = 0 AND {where_clause}").fetchone()[0]
            rows = conn.execute(
                f"SELECT {_COLS_STR} FROM radio_stations WHERE deleted = 0 AND {where_clause} "
                "ORDER BY name ASC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            return PaginatedResult(
                items=[_row_to_station(r) for r in rows],
                total=total, page=page, page_size=page_size,
                pages=max(1, (total + page_size - 1) // page_size),
            )
        finally:
            conn.close()
