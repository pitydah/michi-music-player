"""SQLite persistence — implements SettingsRepository."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.persistence import SettingsRepository
from michi.domain.persistence_health import (
    PersistenceDiagnostic,
    PersistenceHealth,
)
from michi.domain.settings import SettingsState

logger = logging.getLogger(__name__)


def _classify_open_error(exc: sqlite3.Error) -> PersistenceDiagnostic:
    text = str(exc).lower()
    if "locked" in text or "busy" in text:
        return PersistenceDiagnostic(PersistenceHealth.LOCKED, str(exc))
    if "not a database" in text or "malformed" in text:
        return PersistenceDiagnostic(PersistenceHealth.CORRUPT_DATABASE, str(exc))
    if "readonly" in text or "permission" in text or "unable to open" in text:
        return PersistenceDiagnostic(PersistenceHealth.ACCESS_FAILURE, str(exc))
    if "i/o error" in text or "disk" in text:
        return PersistenceDiagnostic(PersistenceHealth.IO_FAILURE, str(exc))
    return PersistenceDiagnostic(PersistenceHealth.CORRUPT_DATABASE, str(exc))


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

    @staticmethod
    def inspect_path(db_path: Path) -> PersistenceDiagnostic:
        """Diagnose persistence health WITHOUT side effects.

        Does not create, delete, rename, or repair anything.
        """
        if not db_path.exists():
            return PersistenceDiagnostic(PersistenceHealth.MISSING)

        try:
            conn = sqlite3.connect(str(db_path), timeout=0.2)
            try:
                check = conn.execute("PRAGMA quick_check").fetchone()
                if check is None or check[0] != "ok":
                    return PersistenceDiagnostic(
                        PersistenceHealth.CORRUPT_DATABASE,
                        f"quick_check: {check}",
                    )
                rows = conn.execute("SELECT key, value FROM settings").fetchall()
            finally:
                conn.close()
        except sqlite3.OperationalError as exc:
            return _classify_open_error(exc)
        except sqlite3.DatabaseError as exc:
            text = str(exc).lower()
            if "not a database" in text or "malformed" in text:
                return PersistenceDiagnostic(
                    PersistenceHealth.CORRUPT_DATABASE, str(exc)
                )
            return PersistenceDiagnostic(PersistenceHealth.CORRUPT_DATABASE, str(exc))
        except OSError as exc:
            return PersistenceDiagnostic(PersistenceHealth.ACCESS_FAILURE, str(exc))

        return SQLiteSettingsRepository._validate_rows(rows)

    @staticmethod
    def _validate_rows(rows: list[tuple]) -> PersistenceDiagnostic:
        for key, value in rows:
            if key == "volume":
                try:
                    vol = int(value)
                except (TypeError, ValueError):
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        f"volume is not an integer: {value!r}",
                    )
                if not 0 <= vol <= 100:
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        f"volume out of range: {vol}",
                    )
            elif key == "muted":
                if value not in ("true", "false"):
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        f"muted is not a boolean string: {value!r}",
                    )
            elif key == "recent_files":
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        "recent_files is not valid JSON",
                    )
                if not isinstance(parsed, list) or not all(
                    isinstance(item, str) for item in parsed
                ):
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        "recent_files is not a list of strings",
                    )
            # Unknown keys are tolerated (forward compatible).
            # last_directory is any string; no validation needed.
        return PersistenceDiagnostic(PersistenceHealth.HEALTHY)

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
