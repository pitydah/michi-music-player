"""SQLite persistence — implements SessionRepository.

The session snapshot lives in the SAME settings key/value table as the
settings repository (key "session_snapshot"), so the row participates in
last-known-good logical-row equality automatically. Only that row is
ever touched; other rows are never modified and journal mode is never
changed.
"""

import logging
import sqlite3
from pathlib import Path

from michi.application.ports import SessionRepository
from michi.domain.session import (
    PlaybackSessionSnapshot,
    decode_snapshot,
    encode_snapshot,
    fresh_snapshot,
)

logger = logging.getLogger(__name__)

SESSION_KEY = "session_snapshot"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class SqliteSessionRepository(SessionRepository):
    """Persists one playback session snapshot in the settings table."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(_SCHEMA)

    def load(self) -> PlaybackSessionSnapshot:
        """Read the snapshot; never raises and never writes.

        Missing row -> fresh snapshot; malformed value -> fresh snapshot
        (the malformed original is left untouched, M11.2C safe read
        fallback); sqlite errors -> logged + fresh snapshot.
        """
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key = ?", (SESSION_KEY,)
                ).fetchone()
        except sqlite3.Error as exc:
            logger.warning(
                "session snapshot load failed (%s); using fresh snapshot", exc
            )
            return fresh_snapshot()

        if row is None:
            return fresh_snapshot()
        return decode_snapshot(row[0])

    def save(self, snapshot: PlaybackSessionSnapshot) -> bool:
        """Upsert the encoded snapshot; sqlite errors are logged + ignored.

        Returns True when the snapshot was durably persisted, False when a
        sqlite error occurred (logged, never raised) — the success signal
        the application uses to decide whether durable state advanced.
        """
        encoded = encode_snapshot(snapshot)
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (SESSION_KEY, encoded),
                )
        except sqlite3.Error as exc:
            logger.warning("session snapshot save failed (%s); ignoring", exc)
            return False
        return True
