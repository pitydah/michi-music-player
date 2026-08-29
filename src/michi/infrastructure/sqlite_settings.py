"""SQLite persistence — implements SettingsRepository."""

import errno
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from contextlib import suppress
from pathlib import Path

from michi.application.persistence import SettingsRepository
from michi.domain.audio_engine import AudioEngineId
from michi.domain.persistence_health import (
    PersistenceDiagnostic,
    PersistenceHealth,
)
from michi.domain.settings import (
    SettingsState,
    WindowGeometry,
    window_geometry_from_json,
    window_geometry_to_json,
)

logger = logging.getLogger(__name__)

# Persisted settings schema version (the settings key/value row
# `schema_version`). Absent or non-integer rows are treated as version 0.
CURRENT_SCHEMA_VERSION = 1

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
_SIDECAR_SUFFIXES = ("-wal", "-shm")


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
        quarantine_path: Path | None = None,
    ) -> None:
        super().__init__(primary_diagnostic.message)
        self.primary_diagnostic = primary_diagnostic
        self.recovery_diagnostic = recovery_diagnostic
        self.recovery_candidate = recovery_candidate
        self.quarantine_path = quarantine_path


class SchemaVersionError(RuntimeError):
    """The database schema is newer than this build supports (fail closed).

    A newer version is never downgraded, rewritten, or treated as the
    current version: the caller must refuse to open and surface the error.
    """


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
    for suffix in _SIDECAR_SUFFIXES:
        _remove_best_effort(Path(str(db_path) + suffix))


def _primary_sidecar_paths(db_path: Path) -> list[Path]:
    """Deterministic -wal/-shm sibling paths of a primary database file."""
    return [Path(str(db_path) + suffix) for suffix in _SIDECAR_SUFFIXES]


def _hash_file(path: Path) -> str:
    """Streaming SHA-256 of a file (64 KiB chunks, never a full read)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file_exclusive(src: Path, dst: Path) -> None:
    """Copy a file into a brand-new destination via O_EXCL (mode 0o600).

    The destination must not pre-exist; a stale or foreign file at the
    destination aborts with FileExistsError instead of being overwritten.
    """
    fd = os.open(dst, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
        while True:
            chunk = inp.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _remove_sqlite_sidecars_strict(db_path: Path) -> None:
    """Strict -wal/-shm removal: FileNotFoundError is fine, all else raises."""
    for suffix in _SIDECAR_SUFFIXES:
        with suppress(FileNotFoundError):
            Path(str(db_path) + suffix).unlink()


# Authoritative logical state for recovery provenance
# (M6-FINAL-CROSS-PERSISTENCE-GATE). These tables carry USER/AUTHORITATIVE
# durable state: settings holds the application/session rows (including the
# M6-FINAL-CROSS-PERSISTENCE-GATE provenance set, extended by M6-EXT-R4-O:
# the library-identity catalog + user state are USER AUTHORITY and MUST be
# protected by M11 recovery — losing LibrarySource/MediaFile/Track ids,
# favorites or playlists is P0. REBUILDABLE CACHE tables (library_index,
# library_meta, library_media_cache) are intentionally EXCLUDED: the
# filesystem is the authority over file existence and the caches can be
# reconstructed — their divergence must never invalidate provenance. Adding
# a future authoritative table means adding it HERE (single source, never
# scattered hardcodes) — and, if the table is optional (pre-existing
# databases legitimately lack it), its optionality MUST be declared
# explicitly in _OPTIONAL_AUTHORITATIVE_TABLES; a required table missing
# from a database is a provenance failure (fail closed), never an empty one.
_AUTHORITATIVE_TABLES = (
    "settings",
    "library_prefs",
    "library_catalog_meta",
    "library_sources",
    "library_media_files",
    "library_tracks",
    "library_favorites",
    "library_history",
    "library_recently_added",
)
# Every table born in M6-EXT-R4 is optional ONLY for PRE-R4 databases
# (absent == empty); settings stays required (settings-less is never an
# empty DB). Once the R4-era marker (library_catalog_meta) EXISTS, the
# whole identity catalog + user state become REQUIRED — a missing table in
# an R4 database is corruption, never an empty state (fail closed).
_OPTIONAL_AUTHORITATIVE_TABLES = frozenset(
    {
        "library_prefs",
        "library_catalog_meta",
        "library_sources",
        "library_media_files",
        "library_tracks",
        "library_favorites",
        "library_history",
        "library_recently_added",
    }
)

# R4-era identity tables: required once the era marker exists.
_R4_ERA_MARKER = "library_catalog_meta"
_R4_ERA_TABLES = frozenset(
    {
        "library_catalog_meta",
        "library_sources",
        "library_media_files",
        "library_tracks",
        "library_favorites",
        "library_history",
        "library_recently_added",
    }
)

# Row shape per authoritative table (ordered, deterministic). Key/value
# tables keep (key, value); identity tables compare their full ordered rows.
_AUTHORITATIVE_QUERIES = {
    "settings": "SELECT key, value FROM settings ORDER BY key",
    "library_prefs": "SELECT key, value FROM library_prefs ORDER BY key",
    "library_catalog_meta": (
        "SELECT key, value FROM library_catalog_meta ORDER BY key"
    ),
    "library_sources": (
        "SELECT library_source_id, display_name, root_path, enabled, "
        "lifecycle, created_at_ms, updated_at_ms FROM library_sources "
        "ORDER BY library_source_id"
    ),
    "library_media_files": (
        "SELECT media_file_id, library_source_id, relative_path, "
        "last_known_path, availability, created_at_ms, updated_at_ms "
        "FROM library_media_files ORDER BY media_file_id"
    ),
    "library_tracks": (
        "SELECT track_id, media_file_id, created_at_ms FROM library_tracks "
        "ORDER BY track_id"
    ),
    "library_favorites": "SELECT track_id FROM library_favorites ORDER BY track_id",
    "library_history": (
        "SELECT position, track_id FROM library_history ORDER BY position"
    ),
    "library_recently_added": (
        "SELECT position, track_id FROM library_recently_added ORDER BY position"
    ),
}


def _read_authoritative_state(path: Path) -> dict[str, list[tuple]]:
    """Logical authoritative state of a database: ordered rows of every
    authoritative table, read-only.

    An ABSENT OPTIONAL authoritative table is equivalent to an EMPTY one; a
    NON-empty table is never equivalent to a missing one. An absent REQUIRED
    table (``settings``) raises — the candidate provenance FAILS CLOSED; a
    settings-less database is never silently treated as an empty settings
    database. Rebuildable cache tables are never part of the provenance
    identity. Structural/operational errors propagate to the caller (fail
    closed in _candidate_matches_lkg).
    """
    conn = sqlite3.connect(_read_only_uri(path), uri=True, timeout=0.2)
    try:
        state: dict[str, list[tuple]] = {}
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        r4_era = _R4_ERA_MARKER in existing
        for table in _AUTHORITATIVE_TABLES:
            try:
                rows = conn.execute(_AUTHORITATIVE_QUERIES[table]).fetchall()
            except sqlite3.OperationalError as exc:
                if (
                    "no such table" in str(exc).lower()
                    and table in _OPTIONAL_AUTHORITATIVE_TABLES
                    and not (r4_era and table in _R4_ERA_TABLES)
                ):
                    rows = []  # absent optional authoritative table == empty
                else:
                    raise  # required table missing: provenance fails closed
            state[table] = [tuple(row) for row in rows]
        return state
    finally:
        conn.close()


def _candidate_matches_lkg(candidate_path: Path, lkg_path: Path) -> bool:
    """Logical (row-level) equality of the AUTHORITATIVE state between
    candidate and LKG; fail closed. Rebuildable cache divergence never
    invalidates provenance (M6-FINAL-CROSS-PERSISTENCE-GATE)."""
    try:
        return _read_authoritative_state(candidate_path) == _read_authoritative_state(
            lkg_path
        )
    except (sqlite3.Error, OSError):
        return False


def _install_recovery_candidate(candidate_path: Path, db_path: Path) -> None:
    """Atomically install a validated recovery candidate over the primary.

    os.replace is the single install boundary — never copy, truncate, or
    SQL-restore. The candidate path ceases to exist; the primary is
    replaced in one atomic rename.
    """
    os.replace(candidate_path, db_path)


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


def _decode_theme(raw: object) -> tuple[str, bool]:
    """Decode a persisted theme value into (value, malformed).

    Text is preserved exactly (the theme namespace is open-ended); any
    non-text row (e.g. an integer or BLOB inserted directly) is malformed
    and falls back to the domain default ("dark").
    """
    if isinstance(raw, str):
        return raw, False
    return "dark", True


def _decode_window_geometry(raw: object) -> tuple[WindowGeometry, bool]:
    """Decode a persisted window_geometry value into (geometry, malformed).

    Strict-JSON decode rules (canonical implementation lives in the domain
    helper so the presentation bridge can share them without importing
    infrastructure): width/height must be present and positive; x/y may be
    null or any integer (negative legitimate); maximized must be a boolean
    when present. Missing keys default (x/y -> None, maximized -> False);
    any violation falls back to WindowGeometry() with malformed=True.
    """
    return window_geometry_from_json(raw)


def _migrate_0_to_1(conn: sqlite3.Connection) -> None:
    """Apply the v0 -> v1 migration inside a single transaction.

    The caller passes a connection opened in autocommit mode
    (``isolation_level=None``); this function owns BEGIN/COMMIT/ROLLBACK.
    On any failure the transaction is rolled back and re-raised — no
    partial new state is ever authoritative.
    """
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('schema_version', '1') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


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
        self._migrate_schema()

    def _ensure_schema(self) -> None:
        # Explicit close (M5-PRODUCTION-LIFECYCLE-GATE): the with-conn only
        # commits; close deterministically instead of waiting for GC.
        # close() would ROLL BACK a pending transaction — commit explicitly
        # to preserve the with-conn's commit-on-exit.
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(self._SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _migrate_schema(self) -> None:
        """Version-check and migrate the persisted schema (writable path only).

        READ FIRST, DECIDE SECOND, WRITE ONLY WHEN AUTHORIZED: this runs
        exclusively in the writable constructor flow — never from the
        read-only preflight (inspect_path / LKG inspection). Version
        interpretation: absent or non-integer row -> 0 (malformed is
        warned and treated as v0, per the M11.2C field fallback
        philosophy); a version newer than supported fails closed with
        SchemaVersionError (never downgrade, never rewrite, never pretend
        it is the current version).
        """
        conn = sqlite3.connect(str(self._db_path), isolation_level=None, timeout=0.2)
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'schema_version'"
            ).fetchone()
            raw = row[0] if row is not None else None
            if raw is None or not str(raw).isdigit():
                if raw is not None:
                    logger.warning(
                        "Malformed schema_version %r — treating as v0 and migrating",
                        raw,
                    )
                current = 0
            else:
                current = int(raw)
            if current == CURRENT_SCHEMA_VERSION:
                return
            if current > CURRENT_SCHEMA_VERSION:
                raise SchemaVersionError(
                    f"database schema version {current} is newer than "
                    f"supported {CURRENT_SCHEMA_VERSION}; refusing to open"
                )
            _migrate_0_to_1(conn)
        finally:
            conn.close()

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
                # M6-EXT-R4-O: an R4-era database (library_catalog_meta
                # present) REQUIRES the whole identity catalog + user state;
                # a missing R4 table is corruption — never an empty state.
                if _R4_ERA_MARKER in table_names:
                    missing_r4 = sorted(_R4_ERA_TABLES - table_names)
                    if missing_r4:
                        return PersistenceDiagnostic(
                            PersistenceHealth.MALFORMED_DATA,
                            f"R4 identity tables missing: {missing_r4}",
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
        # M5.C6: theme/window_geometry rows are intentionally NOT validated
        # here — same additive-safe choice as last_directory/schema_version.
        # Their malformed-data handling lives in load()'s per-field decoders
        # (M11.2C field fallback); inspect_path stays HEALTHY for any
        # string-typed row under those keys.
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
    def quarantine_root_path(db_path: Path) -> Path:
        """Deterministic sibling directory holding quarantine generations."""
        return Path(str(db_path) + ".quarantine")

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
                # M6-EXT-R4-O: an R4-era database missing any identity
                # catalog/user-state table is STRUCTURALLY malformed — the
                # recovery route (LKG restore) must trigger, never a silent
                # open of a database that lost user authority.
                table_names = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                if _R4_ERA_MARKER in table_names and _R4_ERA_TABLES - table_names:
                    return False
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
        cls,
        db_path: Path,
        primary_diag: PersistenceDiagnostic,
        recovery_diagnostic: PersistenceDiagnostic | None = None,
        quarantine_path: Path | None = None,
    ) -> PersistenceStartupError:
        """Build the startup failure for unrecoverable primaries.

        Never stages and never installs. An existing candidate is preserved
        and reported as-is (its diagnostic is inspected lazily); quarantine
        material is reported verbatim.
        """
        candidate = cls.recovery_candidate_path(db_path)
        if recovery_diagnostic is None and candidate.exists():
            recovery_diagnostic = cls.inspect_path(candidate)
        return PersistenceStartupError(
            primary_diag,
            recovery_diagnostic=recovery_diagnostic,
            recovery_candidate=candidate if candidate.exists() else None,
            quarantine_path=quarantine_path,
        )

    @classmethod
    def _recover_or_raise(
        cls, db_path: Path, primary_diag: PersistenceDiagnostic
    ) -> "SQLiteSettingsRepository":
        """Validate a trusted candidate, quarantine originals, install safely.

        Every abort path raises PersistenceStartupError; there are no retry
        loops. The LKG snapshot is preserved (never deleted or refreshed)
        through the whole recovery. Owned staged candidates are discarded on
        provenance/quarantine-phase aborts (no primary mutation occurred), but
        preserved on strict-removal/install aborts (trusted resume material);
        pre-existing candidates are never deleted.
        """
        candidate = cls.recovery_candidate_path(db_path)
        lkg = cls.last_known_good_path(db_path)
        owns_candidate = False
        quarantine_path: Path | None = None

        # 1. LKG authorization: recovery requires a healthy LKG.
        if not lkg.exists():
            raise cls._recovery_failure(db_path, primary_diag)
        lkg_diag = cls.inspect_path(lkg)
        if lkg_diag.health is not PersistenceHealth.HEALTHY:
            raise cls._recovery_failure(
                db_path, primary_diag, recovery_diagnostic=lkg_diag
            )

        # 2. Candidate trust/staging.
        if candidate.exists():
            if candidate.is_symlink():
                raise cls._recovery_failure(db_path, primary_diag)
            if any(
                Path(str(candidate) + suffix).exists() for suffix in _SIDECAR_SUFFIXES
            ):
                raise cls._recovery_failure(db_path, primary_diag)
            cand_diag = cls.inspect_path(candidate)
            if cand_diag.health is not PersistenceHealth.HEALTHY:
                raise cls._recovery_failure(
                    db_path, primary_diag, recovery_diagnostic=cand_diag
                )
        else:
            stage_diag = cls.stage_recovery_from_last_known_good(db_path, candidate)
            if stage_diag.health is not PersistenceHealth.HEALTHY:
                raise PersistenceStartupError(
                    primary_diag, recovery_diagnostic=stage_diag
                )
            owns_candidate = True

        # 3. Provenance: candidate rows must equal LKG rows (fail closed).
        if not _candidate_matches_lkg(candidate, lkg):
            if owns_candidate:
                _remove_best_effort(candidate)
                _remove_sqlite_sidecars(candidate)
            raise cls._recovery_failure(db_path, primary_diag)
        _remove_sqlite_sidecars(candidate)

        # 4. Quarantine original primary artifacts (byte-exact evidence).
        artifacts = [db_path] + _primary_sidecar_paths(db_path)
        if any(artifact.exists() for artifact in artifacts):
            try:
                quarantine_path = _quarantine_primary_artifacts(db_path)
            except OSError as exc:
                if owns_candidate:
                    _remove_best_effort(candidate)
                    _remove_sqlite_sidecars(candidate)
                raise PersistenceStartupError(
                    primary_diag,
                    recovery_diagnostic=_classify_os_error(exc),
                ) from exc

        # 5. Strict removal of original sidecars (any failure aborts).
        try:
            _remove_sqlite_sidecars_strict(db_path)
        except OSError as exc:
            raise PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=_classify_os_error(exc),
                quarantine_path=quarantine_path,
            ) from exc

        # 6. Atomic install of the trusted candidate.
        try:
            _install_recovery_candidate(candidate, db_path)
        except OSError as exc:
            raise PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=_classify_os_error(exc),
                quarantine_path=quarantine_path,
            ) from exc

        # 7. Post-install hygiene (candidate path no longer exists).
        _remove_sqlite_sidecars(candidate)

        # 8. Post-install verification; no rollback to quarantined corrupt data.
        final_diag = cls.inspect_path(db_path)
        if final_diag.health is not PersistenceHealth.HEALTHY:
            raise PersistenceStartupError(final_diag, quarantine_path=quarantine_path)

        # 9. Only now open writable; construction failures surface as
        #    PersistenceStartupError rather than leaking raw exceptions.
        try:
            repo = cls(db_path)
        except sqlite3.Error as exc:
            raise PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=_classify_sqlite_error(exc),
                quarantine_path=quarantine_path,
            ) from exc
        except OSError as exc:
            raise PersistenceStartupError(
                primary_diag,
                recovery_diagnostic=_classify_os_error(exc),
                quarantine_path=quarantine_path,
            ) from exc

        # 10. Observability: exactly one warning, never setting values.
        if quarantine_path is not None:
            logger.warning(
                "settings persistence recovered automatically from LKG "
                "after %s; original artifacts quarantined at %s",
                primary_diag.health.name,
                quarantine_path,
            )
        else:
            logger.warning(
                "settings persistence recovered automatically from LKG "
                "after %s; no original artifacts to quarantine",
                primary_diag.health.name,
            )

        return repo

    @classmethod
    def _open_missing(
        cls, db_path: Path, primary_diag: PersistenceDiagnostic
    ) -> "SQLiteSettingsRepository":
        """Handle a missing primary: true first run, or recovery routing."""
        candidate = cls.recovery_candidate_path(db_path)
        lkg = cls.last_known_good_path(db_path)
        has_sidecars = any(p.exists() for p in _primary_sidecar_paths(db_path))
        if not candidate.exists() and not lkg.exists() and not has_sidecars:
            # True first run: create the primary, verify, seed the LKG.
            repo = cls(db_path)
            verify = cls.inspect_path(db_path)
            if verify.health is not PersistenceHealth.HEALTHY:
                raise PersistenceStartupError(verify)
            cls._refresh_lkg_best_effort(db_path)
            return repo
        if not lkg.exists():
            # Orphan sidecars or a candidate without LKG: preserve everything,
            # never create a blank database over evidence.
            raise cls._recovery_failure(db_path, primary_diag)
        return cls._recover_or_raise(db_path, primary_diag)

    @classmethod
    def open_for_startup(cls, db_path: Path) -> "SQLiteSettingsRepository":
        """Open the settings repository with a startup preflight.

        Read-only inspection decides the route before any writable open.
        Recoverable primaries (MISSING / CORRUPT_DATABASE / structural
        MALFORMED_DATA with a healthy LKG) are auto-restored from a trusted
        candidate; terminal states raise PersistenceStartupError.
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
                return cls._recover_or_raise(db_path, diag)
            raise PersistenceStartupError(probe)

        if health is PersistenceHealth.CORRUPT_DATABASE:
            return cls._recover_or_raise(db_path, diag)

        # LOCKED / ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE:
        # no fallback, no staging, no writable open.
        raise PersistenceStartupError(diag)

    def load(self) -> SettingsState:
        state = SettingsState()
        # Explicit close (M5-PRODUCTION-LIFECYCLE-GATE): the with-conn only
        # commits; close deterministically instead of waiting for GC.
        conn = sqlite3.connect(str(self._db_path))
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        finally:
            conn.close()

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
            elif key == "theme":
                state.theme, malformed = _decode_theme(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'theme'; using default 'dark'"
                    )
            elif key == "window_geometry":
                state.window_geometry, malformed = _decode_window_geometry(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'window_geometry'; "
                        "using default geometry"
                    )
            elif key == "online_enrichment":
                state.online_enrichment, malformed = _decode_online_enrichment(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'online_enrichment'; "
                        "using default False"
                    )
            elif key == "audio_engine_id":
                state.audio_engine_id, malformed = _decode_audio_engine_id(value)
                if malformed:
                    logger.warning(
                        "invalid persisted setting 'audio_engine_id'; "
                        "using default qt_multimedia"
                    )
        return state

    def save(self, state: SettingsState) -> None:
        rows = [
            ("volume", str(state.volume)),
            ("muted", str(state.muted).lower()),
            ("last_directory", state.last_directory),
            ("recent_files", json.dumps(state.recent_files)),
            ("theme", state.theme),
            ("window_geometry", window_geometry_to_json(state.window_geometry)),
            ("online_enrichment", str(state.online_enrichment).lower()),
            ("audio_engine_id", state.audio_engine_id.value),
        ]
        # Explicit close (M5-PRODUCTION-LIFECYCLE-GATE): the with-conn only
        # commits; close deterministically instead of waiting for GC.
        # close() would ROLL BACK a pending transaction — commit explicitly
        # to preserve the with-conn's commit-on-exit.
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)
            conn.commit()
        finally:
            conn.close()


def _decode_online_enrichment(raw: object) -> tuple[bool, bool]:
    """M6.9: strict boolean decode; anything else -> default False."""
    if isinstance(raw, str) and raw.strip().lower() in {"true", "false"}:
        return raw.strip().lower() == "true", False
    return False, True


def _decode_audio_engine_id(raw: object) -> tuple[AudioEngineId, bool]:
    """M11.3F: strict decode against AudioEngineId canonical values.

    Only the exact persistence-safe strings ("qt_multimedia", "gstreamer",
    "mpd") decode. Anything else (empty, wrong case, unknown id, BLOB /
    non-text) is FIELD-LEVEL malformed: fall back to QT_MULTIMEDIA with
    malformed=True. NEVER triggers database recovery/quarantine — a bad
    preference is not database corruption.
    """
    if isinstance(raw, str):
        for engine in AudioEngineId:
            if raw == engine.value:
                return engine, False
    return AudioEngineId.QT_MULTIMEDIA, True


def _quarantine_primary_artifacts(db_path: Path) -> Path:
    """Quarantine the original primary + -wal/-shm artifacts byte-exact.

    Each run creates a fresh `recovery-*` generation under
    ``<db>.quarantine`` (0700). Copies are made O_EXCL (0600) and verified
    by size + SHA-256 before the generation is considered complete. The
    quarantine is evidence only — never a recovery source. On any OSError
    the owned incomplete generation is removed and the error re-raised;
    the primary, candidate, and LKG are never touched.
    """
    root = SQLiteSettingsRepository.quarantine_root_path(db_path)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise OSError(errno.ENOTDIR, f"quarantine root is not a directory: {root}")
    if not root.exists():
        root.mkdir(mode=0o700)
    generation = Path(tempfile.mkdtemp(prefix="recovery-", dir=root))
    try:
        for artifact in [db_path] + _primary_sidecar_paths(db_path):
            if not artifact.exists():
                continue
            dest = generation / artifact.name
            _copy_file_exclusive(artifact, dest)
            if artifact.stat().st_size != dest.stat().st_size or _hash_file(
                artifact
            ) != _hash_file(dest):
                raise OSError(
                    errno.EIO, f"quarantine verification failed: {artifact.name}"
                )
    except OSError:
        shutil.rmtree(generation, ignore_errors=True)
        raise
    return generation
