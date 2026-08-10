"""SQLite persistence — implements SettingsRepository."""

import json
import sqlite3
from pathlib import Path

from michi.application.persistence import SettingsRepository
from michi.domain.settings import SettingsState


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
        db_path = str(self._db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(self._SCHEMA)

    def load(self) -> SettingsState:
        state = SettingsState()
        try:
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
                        state.recent_files = json.loads(value)
        except Exception:
            pass  # first launch, no settings yet
        return state

    def save(self, state: SettingsState) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("INSERT OR REPLACE INTO settings VALUES ('volume', ?)", (str(state.volume),))
            conn.execute("INSERT OR REPLACE INTO settings VALUES ('muted', ?)", (str(state.muted).lower(),))
            conn.execute("INSERT OR REPLACE INTO settings VALUES ('last_directory', ?)", (state.last_directory,))
            conn.execute("INSERT OR REPLACE INTO settings VALUES ('recent_files', ?)", (json.dumps(state.recent_files),))
