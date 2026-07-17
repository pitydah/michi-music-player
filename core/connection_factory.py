"""LibraryConnectionFactory — thread-safe read-only SQLite connections.

Each thread gets its own connection via threading.local.
Production connections use URI mode read-only.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
import contextlib

logger = logging.getLogger(__name__)

_local = threading.local()


class LibraryConnectionFactory:
    def __init__(self, db_path: str, timeout_ms: int = 5000):
        logger.debug("LibraryConnectionFactory.__init__ called")
        self._db_path = db_path
        self._timeout = timeout_ms

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(_local, "conn") or _local.conn is None:
            uri = f"file:{Path(self._db_path).resolve()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=self._timeout / 1000.0)
            conn.execute("PRAGMA query_only = 1")
            conn.execute(f"PRAGMA busy_timeout = {self._timeout}")
            _local.conn = conn
        return _local.conn

    def close_all(self):
        if hasattr(_local, "conn") and _local.conn is not None:
            with contextlib.suppress(Exception):
                _local.conn.close()
            _local.conn = None

    @property
    def db_path(self) -> str:
        return self._db_path
