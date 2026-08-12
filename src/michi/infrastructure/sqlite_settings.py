"""SQLite persistence — implements SettingsRepository."""

import errno
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

# SQLite primary result codes (standard constants from sqlite3 module)
_SQLITE_BUSY = sqlite3.SQLITE_BUSY
_SQLITE_LOCKED = sqlite3.SQLITE_LOCKED
_SQLITE_READONLY = sqlite3.SQLITE_READONLY
_SQLITE_IOERR = sqlite3.SQLITE_IOERR
_SQLITE_CORRUPT = sqlite3.SQLITE_CORRUPT
_SQLITE_CANTOPEN = sqlite3.SQLITE_CANTOPEN
_SQLITE_PERM = sqlite3.SQLITE_PERM
_SQLITE_NOTADB = sqlite3.SQLITE_NOTADB

_ACCESS_CODES = {_SQLITE_READONLY, _SQLITE_CANTOPEN, _SQLITE_PERM}
_IO_CODES = {_SQLITE_IOERR}


def _primary_sqlite_code(code: int | None) -> int | None:
    """Normalize an extended SQLite result code to its primary code.

    SQLite extended result codes preserve the primary result code in the
    low 8 bits (e.g. SQLITE_IOERR_SHMOPEN = SQLITE_IOERR | (18 << 8)).
    """
    if code is None:
        return None
    return code & 0xFF


def _classify_sqlite_error(exc: sqlite3.Error) -> PersistenceDiagnostic:
    """Classify a SQLite error conservatively.

    Error codes are authoritative. Unknown errors become UNKNOWN_FAILURE,
    never CORRUPT_DATABASE. A false-negative corruption classification is
    safer than a false positive that could trigger destructive recovery.
    """
    code = _primary_sqlite_code(getattr(exc, "sqlite_errorcode", None))

    if code in (_SQLITE_CORRUPT, _SQLITE_NOTADB):
        return PersistenceDiagnostic(PersistenceHealth.CORRUPT_DATABASE, str(exc))
    if code in (_SQLITE_BUSY, _SQLITE_LOCKED):
        return PersistenceDiagnostic(PersistenceHealth.LOCKED, str(exc))
    if code in _ACCESS_CODES:
        return PersistenceDiagnostic(PersistenceHealth.ACCESS_FAILURE, str(exc))
    if code in _IO_CODES:
        return PersistenceDiagnostic(PersistenceHealth.IO_FAILURE, str(exc))

    # Textual fallback only for environments without error codes
    text = str(exc).lower()
    if "not a database" in text or "disk image is malformed" in text:
        return PersistenceDiagnostic(PersistenceHealth.CORRUPT_DATABASE, str(exc))
    if "database is locked" in text or "database table is locked" in text:
        return PersistenceDiagnostic(PersistenceHealth.LOCKED, str(exc))
    if (
        "readonly" in text
        or "permission" in text
        or "unable to open database file" in text
    ):
        return PersistenceDiagnostic(PersistenceHealth.ACCESS_FAILURE, str(exc))
    if "disk i/o error" in text:
        return PersistenceDiagnostic(PersistenceHealth.IO_FAILURE, str(exc))

    return PersistenceDiagnostic(PersistenceHealth.UNKNOWN_FAILURE, str(exc))


def _classify_os_error(exc: OSError) -> PersistenceDiagnostic:
    if exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
        return PersistenceDiagnostic(PersistenceHealth.ACCESS_FAILURE, str(exc))
    if exc.errno in (errno.EIO, errno.ENOSPC):
        return PersistenceDiagnostic(PersistenceHealth.IO_FAILURE, str(exc))
    return PersistenceDiagnostic(PersistenceHealth.UNKNOWN_FAILURE, str(exc))


def _read_only_uri(db_path: Path) -> str:
    return f"{db_path.resolve().as_uri()}?mode=ro"


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

        Opens read-only. Does not create, delete, rename, repair, or
        migrate anything. Never alters journal mode.
        """
        if not db_path.exists():
            return PersistenceDiagnostic(PersistenceHealth.MISSING)

        try:
            conn = sqlite3.connect(_read_only_uri(db_path), uri=True, timeout=0.2)
            try:
                check = conn.execute("PRAGMA quick_check").fetchone()
                if check is None or check[0] != "ok":
                    return PersistenceDiagnostic(
                        PersistenceHealth.CORRUPT_DATABASE,
                        f"quick_check: {check}",
                    )
                schema_rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                table_names = {name for (name,) in schema_rows}
                if "settings" not in table_names:
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        "settings table is missing",
                    )
                cols = conn.execute("PRAGMA table_info(settings)").fetchall()
                col_names = {c[1] for c in cols}
                if not {"key", "value"}.issubset(col_names):
                    return PersistenceDiagnostic(
                        PersistenceHealth.MALFORMED_DATA,
                        "settings table is missing key/value columns",
                    )
                rows = conn.execute("SELECT key, value FROM settings").fetchall()
            finally:
                conn.close()
        except sqlite3.OperationalError as exc:
            return _classify_sqlite_error(exc)
        except sqlite3.DatabaseError as exc:
            return _classify_sqlite_error(exc)
        except OSError as exc:
            return _classify_os_error(exc)

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
