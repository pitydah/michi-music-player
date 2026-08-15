"""SQLite persistence — implements SettingsRepository."""

import errno
import json
import logging
import os
import sqlite3
import tempfile
from contextlib import suppress
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


class PersistenceStartupError(RuntimeError):
    """Policy-level startup failure; may transport diagnostics + candidate."""

    def __init__(
        self,
        primary_diagnostic: PersistenceDiagnostic,
        recovery_diagnostic: PersistenceDiagnostic | None = None,
        recovery_candidate: Path | None = None,
    ) -> None:
        super().__init__(primary_diagnostic.message)
        self.primary_diagnostic = primary_diagnostic
        self.recovery_diagnostic = recovery_diagnostic
        self.recovery_candidate = recovery_candidate


def _read_only_uri(db_path: Path) -> str:
    return f"{db_path.resolve().as_uri()}?mode=ro"


def _sqlite_backup_to_new(source_path: Path, dest_path: Path) -> None:
    """Copy a database into a fresh destination using the SQLite backup API.

    The backup API reads through WAL frames, so committed-but-uncheckpointed
    changes are included — unlike a raw copy of the main database file.
    """
    source_conn = sqlite3.connect(_read_only_uri(source_path), uri=True, timeout=0.2)
    dest_conn = sqlite3.connect(str(dest_path))
    try:
        source_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        source_conn.close()


def _reserve_new_file(path: Path) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)


def _remove_best_effort(path: Path) -> None:
    with suppress(OSError):
        path.unlink(missing_ok=True)


def _remove_sqlite_sidecars(db_path: Path) -> None:
    """Best-effort removal of -wal/-shm sidecars of a closed database file."""
    for suffix in ("-wal", "-shm"):
        _remove_best_effort(Path(str(db_path) + suffix))


def _decode_volume(raw: object) -> tuple[int, bool]:
    """Decode a persisted volume value into (value, malformed).

    Valid values are integer textual representations within 0..100. No
    clamping and no float parsing; anything else is malformed and falls
    back to the domain default (80).
    """
    if not isinstance(raw, str):
        return 80, True
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 80, True
    if not 0 <= value <= 100:
        return 80, True
    return value, False


def _decode_muted(raw: object) -> tuple[bool, bool]:
    """Decode a persisted muted value into (value, malformed).

    The canonical persisted representation is the boolean string "true" or
    "false" as written by save(), matching the strict contract enforced by
    _validate_rows(). Anything else — including the legacy "1"/"0" forms,
    BLOBs, and booleans — is malformed and falls back to the domain
    default (False).
    """
    if raw == "true":
        return True, False
    if raw == "false":
        return False, False
    return False, True


def _decode_last_directory(raw: object) -> tuple[str, bool]:
    """Decode a persisted last_directory value into (value, malformed).

    Text is preserved exactly (no resolve/expanduser/strip/fs checks).
    Non-text (e.g. a BLOB inserted directly) is malformed.
    """
    if isinstance(raw, str):
        return raw, False
    return "", True


def _decode_recent_files(raw: object) -> tuple[list[str], bool]:
    """Decode a persisted recent_files value into (value, malformed).

    Valid values are JSON arrays whose members are all strings. Any
    invalid case (bad JSON, object, scalar, mixed array) is malformed and
    falls back to the domain default ([]) — no member coercion, no
    partial salvage.
    """
    if not isinstance(raw, str):
        return [], True
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return [], True
    if not isinstance(parsed, list) or not all(
        isinstance(item, str) for item in parsed
    ):
        return [], True
    return parsed, False


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

    @staticmethod
    def last_known_good_path(db_path: Path) -> Path:
        """Deterministic sibling path for the single last-known-good snapshot."""
        return Path(str(db_path) + ".lkg")

    @staticmethod
    def refresh_last_known_good(db_path: Path) -> PersistenceDiagnostic:
        """Atomically refresh the last-known-good snapshot from a healthy primary.

        Only a fully validated candidate is promoted via os.replace. The
        existing snapshot is never deleted first and survives every failure.
        """
        diag = SQLiteSettingsRepository.inspect_path(db_path)
        if diag.health is not PersistenceHealth.HEALTHY:
            return diag

        lkg_path = SQLiteSettingsRepository.last_known_good_path(db_path)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=db_path.parent, delete=False
            ) as candidate:
                temp_path = Path(candidate.name)
            _sqlite_backup_to_new(db_path, temp_path)
            candidate_diag = SQLiteSettingsRepository.inspect_path(temp_path)
            if candidate_diag.health is not PersistenceHealth.HEALTHY:
                return candidate_diag
            _remove_sqlite_sidecars(temp_path)
            os.replace(temp_path, lkg_path)
            temp_path = None
        except sqlite3.Error as exc:
            return _classify_sqlite_error(exc)
        except OSError as exc:
            return _classify_os_error(exc)
        finally:
            if temp_path is not None:
                _remove_best_effort(temp_path)
                _remove_sqlite_sidecars(temp_path)

        final_diag = SQLiteSettingsRepository.inspect_path(lkg_path)
        _remove_sqlite_sidecars(lkg_path)
        return final_diag

    @staticmethod
    def stage_recovery_from_last_known_good(
        db_path: Path, destination_path: Path
    ) -> PersistenceDiagnostic:
        """Stage a recovery candidate from the LKG snapshot, non-destructively.

        The primary database is never opened for writing — it is only used to
        derive the LKG path. Programming misuse raises ValueError/FileExistsError.
        """
        resolved_db = db_path.resolve()
        resolved_destination = destination_path.resolve()
        resolved_lkg = SQLiteSettingsRepository.last_known_good_path(db_path).resolve()
        if resolved_destination == resolved_db:
            raise ValueError("destination resolves to the primary database")
        if resolved_destination == resolved_lkg:
            raise ValueError("destination resolves to the last-known-good file")
        if destination_path.exists():
            raise FileExistsError(f"destination already exists: {destination_path}")

        lkg_path = SQLiteSettingsRepository.last_known_good_path(db_path)
        diag = SQLiteSettingsRepository.inspect_path(lkg_path)
        if diag.health is not PersistenceHealth.HEALTHY:
            return diag

        owns_destination = False
        try:
            _reserve_new_file(destination_path)
            owns_destination = True
        except FileExistsError:
            raise
        except OSError as exc:
            return _classify_os_error(exc)

        try:
            _sqlite_backup_to_new(lkg_path, destination_path)
        except sqlite3.Error as exc:
            if owns_destination:
                _remove_best_effort(destination_path)
                _remove_sqlite_sidecars(destination_path)
            return _classify_sqlite_error(exc)
        except OSError as exc:
            if owns_destination:
                _remove_best_effort(destination_path)
                _remove_sqlite_sidecars(destination_path)
            return _classify_os_error(exc)

        final_diag = SQLiteSettingsRepository.inspect_path(destination_path)
        if final_diag.health is not PersistenceHealth.HEALTHY:
            if owns_destination:
                _remove_best_effort(destination_path)
                _remove_sqlite_sidecars(destination_path)
            return final_diag
        _remove_sqlite_sidecars(destination_path)
        return final_diag

    @staticmethod
    def recovery_candidate_path(db_path: Path) -> Path:
        """Deterministic sibling path for the staged recovery candidate."""
        return Path(str(db_path) + ".recovery")

    @staticmethod
    def _structural_probe(db_path: Path) -> bool | PersistenceDiagnostic:
        """Read-only probe: structural readability of settings rows.

        Returns:
            True: the settings table and key/value columns are readable
                (field-level malformed data still satisfies this).
            False: genuinely structural malformation (missing settings table,
                missing key/value columns).
            PersistenceDiagnostic: an operational/environmental failure during
                the probe, classified through the existing taxonomy.
        """
        try:
            conn = sqlite3.connect(_read_only_uri(db_path), uri=True, timeout=0.2)
            try:
                conn.execute("SELECT key, value FROM settings LIMIT 1")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            # SQLite schema-shape errors are STRUCTURAL (False); everything
            # else is operational and reclassified through the taxonomy.
            text = str(exc).lower()
            if "no such table" in text or "no such column" in text:
                return False
            return _classify_sqlite_error(exc)
        except OSError as exc:
            return _classify_os_error(exc)
        return True

    @classmethod
    def _refresh_lkg_best_effort(cls, db_path: Path) -> None:
        """Refresh the LKG snapshot at startup; failure is a warning only."""
        refresh_diag = cls.refresh_last_known_good(db_path)
        if refresh_diag.health is not PersistenceHealth.HEALTHY:
            logger.warning(
                "last-known-good refresh failed at startup (%s); "
                "keeping existing snapshot and continuing: %s",
                refresh_diag.health.name,
                refresh_diag.message,
            )

    @classmethod
    def _recovery_failure(
        cls, db_path: Path, primary_diag: PersistenceDiagnostic
    ) -> PersistenceStartupError:
        """Build the startup failure for unrecoverable primaries.

        Never installs: an existing candidate is preserved as-is; otherwise a
        candidate is staged from a healthy LKG (if present) and reported.
        """
        candidate = cls.recovery_candidate_path(db_path)
        if candidate.exists():
            candidate_diag = cls.inspect_path(candidate)
            return PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=candidate_diag,
                recovery_candidate=candidate,
            )
        lkg = cls.last_known_good_path(db_path)
        if not lkg.exists():
            return PersistenceStartupError(primary_diag)
        lkg_diag = cls.inspect_path(lkg)
        if lkg_diag.health is not PersistenceHealth.HEALTHY:
            return PersistenceStartupError(primary_diag)
        stage_diag = cls.stage_recovery_from_last_known_good(db_path, candidate)
        if stage_diag.health is PersistenceHealth.HEALTHY:
            return PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=stage_diag,
                recovery_candidate=candidate,
            )
        return PersistenceStartupError(primary_diag, recovery_diagnostic=stage_diag)

    @classmethod
    def _open_missing(
        cls, db_path: Path, primary_diag: PersistenceDiagnostic
    ) -> "SQLiteSettingsRepository":
        """Handle a missing primary: first run, or recovery routing."""
        candidate = cls.recovery_candidate_path(db_path)
        if candidate.exists():
            raise cls._recovery_failure(db_path, primary_diag)
        if not cls.last_known_good_path(db_path).exists():
            repo = cls(db_path)
            verify = cls.inspect_path(db_path)
            if verify.health is not PersistenceHealth.HEALTHY:
                raise PersistenceStartupError(verify)
            cls._refresh_lkg_best_effort(db_path)
            return repo
        raise cls._recovery_failure(db_path, primary_diag)

    @classmethod
    def open_for_startup(cls, db_path: Path) -> "SQLiteSettingsRepository":
        """Open the settings repository with a startup preflight.

        Read-only inspection decides the route before any writable open.
        Recovery material is staged — never installed.
        """
        diag = cls.inspect_path(db_path)
        health = diag.health

        if health is PersistenceHealth.HEALTHY:
            cls._refresh_lkg_best_effort(db_path)
            return cls(db_path)

        if health is PersistenceHealth.MISSING:
            return cls._open_missing(db_path, diag)

        if health is PersistenceHealth.MALFORMED_DATA:
            probe = cls._structural_probe(db_path)
            if probe is True:
                return cls(db_path)
            if probe is False:
                raise cls._recovery_failure(db_path, diag)
            raise PersistenceStartupError(probe)

        if health is PersistenceHealth.CORRUPT_DATABASE:
            raise cls._recovery_failure(db_path, diag)

        # LOCKED / ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE:
        # no fallback, no staging, no writable open.
        raise PersistenceStartupError(diag)

    def load(self) -> SettingsState:
        state = SettingsState()
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        for key, value in rows:
            if key == "volume":
                state.volume, malformed = _decode_volume(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'volume'; using default 80"
                    )
            elif key == "muted":
                state.muted, malformed = _decode_muted(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'muted'; using default False"
                    )
            elif key == "last_directory":
                state.last_directory, malformed = _decode_last_directory(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'last_directory'; using default ''"
                    )
            elif key == "recent_files":
                state.recent_files, malformed = _decode_recent_files(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'recent_files'; using default []"
                    )
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
