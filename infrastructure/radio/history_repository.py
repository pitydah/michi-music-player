from __future__ import annotations

import datetime
import sqlite3
from typing import Callable

from core.radio.models import StationId


class SqliteRadioHistoryRepository:
    def __init__(self, db_path: str, clock: Callable[[], str] | None = None):
        self._db_path = db_path
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def initialize(self):
        conn = self._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS radio_stations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT DEFAULT '',
                    stream_url TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS radio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT DEFAULT '',
                    duration INTEGER DEFAULT 0,
                    result TEXT DEFAULT '',
                    error_code TEXT DEFAULT '',
                    metadata_title TEXT DEFAULT '',
                    FOREIGN KEY (station_id) REFERENCES radio_stations(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_radio_history_station
                ON radio_history(station_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_radio_history_started
                ON radio_history(started_at DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def record_play(self, station_id: StationId, title: str = "",
                    result: str = "played", error_code: str = ""):
        now = self._clock()
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO radio_history (station_id, started_at, result, error_code, metadata_title) "
                "VALUES (?, ?, ?, ?, ?)",
                (station_id, now, result, error_code, title),
            )
            conn.commit()
        finally:
            conn.close()

    def update_end(self, history_id: int, ended_at: str, duration: int):
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE radio_history SET ended_at = ?, duration = ? WHERE id = ?",
                (ended_at, duration, history_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT h.*, s.name AS station_name, s.stream_url "
                "FROM radio_history h "
                "LEFT JOIN radio_stations s ON h.station_id = s.id "
                "ORDER BY h.started_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def count_history(self) -> int:
        conn = self._conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM radio_history").fetchone()[0]
        finally:
            conn.close()

    def clear_history(self, retention_days: int | None = None):
        conn = self._conn()
        try:
            if retention_days is not None:
                cutoff = (
                    datetime.datetime.now(datetime.timezone.utc) -
                    datetime.timedelta(days=retention_days)
                ).isoformat()
                conn.execute("DELETE FROM radio_history WHERE started_at < ?", (cutoff,))
            else:
                conn.execute("DELETE FROM radio_history")
            conn.commit()
        finally:
            conn.close()
