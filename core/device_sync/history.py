"""SyncHistoryRepository — persisted device sync history in the app DB.

Single authority for sync history: the application database via the
formal migrations (migration 10 creates ``device_sync_history``). The
facade never keeps an in-memory history list.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("michi.device_sync.history")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS device_sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL DEFAULT '',
    device_id TEXT NOT NULL DEFAULT '',
    device_label TEXT NOT NULL DEFAULT '',
    direction TEXT NOT NULL DEFAULT 'to_device',
    status TEXT NOT NULL DEFAULT 'completed',
    total_bytes INTEGER NOT NULL DEFAULT 0,
    transferred_bytes INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    playlist_path TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
)
"""


class SyncHistoryRepository:
    def __init__(self, db=None):
        """``db`` is the app LibraryDB (exposes ``.conn``). None-safe."""
        self._db = db

    def initialize(self):
        if self._db is None:
            return
        try:
            self._db.conn.execute(_CREATE_SQL)
            self._db.conn.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("SyncHistoryRepository initialize failed: %s", exc)

    def add(self, entry: dict) -> int:
        if self._db is None:
            return 0
        self.initialize()
        try:
            cur = self._db.conn.execute(
                """INSERT INTO device_sync_history
                   (job_id, device_id, device_label, direction, status,
                    total_bytes, transferred_bytes, error, playlist_path,
                    created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.get("job_id", ""),
                    entry.get("device_id", ""),
                    entry.get("device_label", ""),
                    entry.get("direction", "to_device"),
                    entry.get("status", "completed"),
                    int(entry.get("total_bytes", 0) or 0),
                    int(entry.get("transferred_bytes", 0) or 0),
                    entry.get("error", ""),
                    entry.get("playlist_path", ""),
                    float(entry.get("timestamp") or time.time()),
                ),
            )
            self._db.conn.commit()
            return cur.lastrowid or 1
        except Exception as exc:  # noqa: BLE001
            logger.error("SyncHistoryRepository add failed: %s", exc)
            return 0

    def list(self, limit: int = 20, device_id: str = "") -> list[dict]:
        if self._db is None:
            return []
        self.initialize()
        try:
            if device_id:
                rows = self._db.conn.execute(
                    """SELECT * FROM device_sync_history WHERE device_id=?
                       ORDER BY created_at DESC, id DESC LIMIT ?""",
                    (device_id, int(limit)),
                ).fetchall()
            else:
                rows = self._db.conn.execute(
                    """SELECT * FROM device_sync_history
                       ORDER BY created_at DESC, id DESC LIMIT ?""",
                    (int(limit),),
                ).fetchall()
            return [self._row_to_dict(row) for row in rows]
        except Exception as exc:  # noqa: BLE001
            logger.error("SyncHistoryRepository list failed: %s", exc)
            return []

    def last_errors(self, limit: int = 10) -> list[dict]:
        if self._db is None:
            return []
        self.initialize()
        try:
            rows = self._db.conn.execute(
                """SELECT * FROM device_sync_history
                   WHERE error != '' ORDER BY created_at DESC, id DESC
                   LIMIT ?""",
                (int(limit),),
            ).fetchall()
            return [
                {
                    "job_id": row[1],
                    "device": row[3],
                    "status": row[5],
                    "error": row[8],
                    "timestamp": row[10],
                }
                for row in rows
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("SyncHistoryRepository last_errors failed: %s", exc)
            return []

    def clear(self) -> dict:
        if self._db is None:
            return {"ok": False, "error": "HISTORY_UNAVAILABLE"}
        self.initialize()
        try:
            self._db.conn.execute("DELETE FROM device_sync_history")
            self._db.conn.commit()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "job_id": row[1],
            "device": row[3],
            "device_id": row[2],
            "device_label": row[3],
            "direction": row[4],
            "status": row[5],
            "total_bytes": row[6],
            "transferred_bytes": row[7],
            "error": row[8],
            "playlist_path": row[9],
            "timestamp": row[10],
        }
