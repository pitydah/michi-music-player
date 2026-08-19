"""SQLite library index repository (M6.2) — bounded context.

Tables ``library_index`` and ``library_meta`` are owned exclusively by the
library index; the settings/session/prefs tables are never touched and the
M5 ``schema_version`` key space is not reused. Explicit connection close;
all-or-nothing upsert batches; fail-closed on newer schema.
"""

import contextlib
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import LibraryIndexRepository
from michi.domain.library_index import (
    LibraryIndexEntry,
    decode_index_metadata,
    encode_index_metadata,
)

logger = logging.getLogger(__name__)

CURRENT_LIBRARY_INDEX_SCHEMA = 1
_VERSION_KEY = "library_schema_version"


class LibraryIndexSchemaError(RuntimeError):
    """The database library index schema is newer than this build supports."""


class SqliteLibraryIndexRepository(LibraryIndexRepository):
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_index ("
                "track_id TEXT PRIMARY KEY,"
                "file_size INTEGER NOT NULL,"
                "mtime_ns INTEGER NOT NULL,"
                "metadata TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = conn.execute(
                "SELECT value FROM library_meta WHERE key = ?", (_VERSION_KEY,)
            ).fetchone()
            raw = row[0] if row is not None else None
            if raw is None:
                conn.execute(
                    "INSERT INTO library_meta(key, value) VALUES(?, ?)",
                    (_VERSION_KEY, str(CURRENT_LIBRARY_INDEX_SCHEMA)),
                )
            else:
                version = int(raw) if str(raw).isdigit() else 0
                if version > CURRENT_LIBRARY_INDEX_SCHEMA:
                    raise LibraryIndexSchemaError(
                        f"library index schema version {version} is newer "
                        f"than supported {CURRENT_LIBRARY_INDEX_SCHEMA}"
                    )
                # version 0 or 1: idempotent — the canonical row already
                # exists (malformed value falls back to the same path).
                if version == 0:
                    conn.execute(
                        "UPDATE library_meta SET value = ? WHERE key = ?",
                        (str(CURRENT_LIBRARY_INDEX_SCHEMA), _VERSION_KEY),
                    )
        finally:
            conn.close()

    def version(self) -> int:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM library_meta WHERE key = ?", (_VERSION_KEY,)
                ).fetchone()
            finally:
                conn.close()
            if row is None:
                return 0
            return int(row[0]) if str(row[0]).isdigit() else 0
        except sqlite3.Error as exc:
            logger.warning("library index version read failed: %s", exc)
            return 0

    def load_all(self) -> tuple[LibraryIndexEntry, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT track_id, file_size, mtime_ns, metadata "
                    "FROM library_index ORDER BY track_id"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("library index load failed: %s", exc)
            return ()
        entries = []
        for track_id, file_size, mtime_ns, raw in rows:
            metadata = decode_index_metadata(raw)
            if metadata is None:
                logger.warning(
                    "library index row %r has malformed metadata; skipping", track_id
                )
                continue
            entries.append(
                LibraryIndexEntry(
                    track_id=track_id,
                    file_size=file_size,
                    mtime_ns=mtime_ns,
                    metadata=metadata,
                )
            )
        return tuple(entries)

    def upsert_many(self, entries) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute("BEGIN")
                for entry in entries:
                    conn.execute(
                        "INSERT INTO library_index(track_id, file_size, "
                        "mtime_ns, metadata) "
                        "VALUES(?, ?, ?, ?) "
                        "ON CONFLICT(track_id) DO UPDATE SET "
                        "file_size = excluded.file_size, "
                        "mtime_ns = excluded.mtime_ns, "
                        "metadata = excluded.metadata",
                        (
                            entry.track_id,
                            entry.file_size,
                            entry.mtime_ns,
                            encode_index_metadata(entry.metadata),
                        ),
                    )
                conn.execute("COMMIT")
            except Exception:
                with contextlib.suppress(sqlite3.Error):
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("library index upsert failed: %s", exc)

    def remove(self, track_id: str) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM library_index WHERE track_id = ?", (track_id,)
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("library index remove failed: %s", exc)

    def apply_delta(self, upserts, removed) -> None:
        """Atomic durable index mutation (M6-PRODUCTION-INTEGRATION): the
        upserts and removes land in a SINGLE transaction (ROLLBACK on any
        error) — the index can never be left half-applied by a commit."""
        if not upserts and not removed:
            return
        try:
            conn = self._connect()
            try:
                conn.execute("BEGIN")
                for entry in upserts:
                    conn.execute(
                        "INSERT INTO library_index(track_id, file_size, "
                        "mtime_ns, metadata) "
                        "VALUES(?, ?, ?, ?) "
                        "ON CONFLICT(track_id) DO UPDATE SET "
                        "file_size = excluded.file_size, "
                        "mtime_ns = excluded.mtime_ns, "
                        "metadata = excluded.metadata",
                        (
                            entry.track_id,
                            entry.file_size,
                            entry.mtime_ns,
                            encode_index_metadata(entry.metadata),
                        ),
                    )
                for track_id in removed:
                    conn.execute(
                        "DELETE FROM library_index WHERE track_id = ?", (track_id,)
                    )
                conn.execute("COMMIT")
            except Exception:
                with contextlib.suppress(sqlite3.Error):
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("library index apply_delta failed: %s", exc)

    def clear(self) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM library_index")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("library index clear failed: %s", exc)
