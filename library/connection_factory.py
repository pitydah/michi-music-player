"""SQLite connection factory — one writer, N readers.

Concurrency model:

* :class:`ReadConnectionFactory` — one read-only (URI ``mode=ro``) connection
  per thread, stored in :class:`threading.local`. Under WAL, readers never
  block writers, so they may run in parallel.
* :class:`WriterCoordinator` — a single serialized writer connection guarded
  by a :class:`threading.Lock`. All mutations go through :meth:`execute` so
  writes are queued deterministically and never race.

WAL mode is enabled once by ``library.schema.Schema.initialize`` (called from
``LibraryDB.__init__``) and persists in the database file, so every connection
opened here inherits it. ``WriterCoordinator`` re-asserts the pragma on its
connection as a runtime verification.
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3
import threading
from typing import Any

logger = logging.getLogger("michi.library")

# Matches the busy_timeout used by LibraryDB and core.connection_factory.
_BUSY_TIMEOUT_MS = 5000


class ReadConnectionFactory:
    """Creates a read-only connection per thread.

    Each thread gets its own connection via :class:`threading.local`.
    Production connections use URI mode read-only so they can never mutate the
    database by accident.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._local = threading.local()

    def connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(
                f"file:{self._db_path}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
            self._local.conn = conn
        return self._local.conn

    @property
    def db_path(self) -> str:
        return self._db_path

    def close_all(self) -> None:
        """Close this thread's read connection, if any."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            with contextlib.suppress(sqlite3.Error):
                conn.close()
            self._local.conn = None


class WriterCoordinator:
    """Single serialized writer connection.

    All writes are funneled through :meth:`execute`, which holds a process-wide
    lock so concurrent callers are serialized. The connection is created lazily
    on first use.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _ensure_connection(self) -> sqlite3.Connection:
        """Lazily open and configure the writer connection under the lock.

        Centralizes the lazy-init (busy timeout, foreign keys, WAL verification)
        so :meth:`execute` and :meth:`transaction` share identical setup.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._db_path, check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
            self._conn.execute("PRAGMA foreign_keys = ON")
            # Re-assert WAL as a runtime verification. It is set
            # persistently by Schema.initialize and inherited by every
            # connection; this call confirms it and is a no-op once set.
            mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()
            logger.debug(
                "WriterCoordinator opened (WAL=%s)",
                mode[0] if mode else "unknown",
            )
        return self._conn

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            conn = self._ensure_connection()
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    @contextlib.contextmanager
    def transaction(self):
        """Transactional context with commit/rollback.

        Yields the writer connection so a caller can run several statements
        atomically; commits on clean exit, rolls back on any exception. The
        process-wide lock is held for the whole block, serializing the unit of
        work against other writers — mirroring :meth:`execute` semantics.
        """
        with self._lock:
            conn = self._ensure_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    @property
    def db_path(self) -> str:
        return self._db_path

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                with contextlib.suppress(sqlite3.Error):
                    self._conn.close()
                self._conn = None
