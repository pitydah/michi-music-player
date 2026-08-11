"""SQLite persistence — implements SettingsRepository."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.persistence import SettingsRepository
from michi.domain.settings import SettingsState

logger = logging.getLogger(__name__)


class SQLiteSettingsRepository(SettingsRepository):
    """Infrastructure adapter: persists settings to SQLite."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(self._SCHEMA)

    def load(self) -> SettingsState:
        state = SettingsState()
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        for key, value in rows:
            if key == "volume":
                state.volume = int(value)
            elif key == "muted":
                state.muted = value == "true"
            elif key == "last_directory":
                state.last_directory = value
            elif key == "recent_files":
                try:
                    state.recent_files = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning("Corrupted recent_files JSON; resetting")
                    state.recent_files = []
        return state

    def save(self, state: SettingsState) -> None:
        rows = [
            ("volume", str(state.volume)),
            ("muted", str(state.muted).lower()),
            ("last_directory", state.last_directory),
            ("recent_files", json.dumps(state.recent_files)),
        ]
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)
