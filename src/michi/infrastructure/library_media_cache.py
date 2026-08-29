"""Rebuildable physical media cache (M6-EXT-R4-K).

CACHE, not user authority: fingerprints + relocation evidence keyed by
MediaFileId. Loss is recoverable (a full scan rebuilds it). Device/inode
are SAME-FILESYSTEM RELOCATION HINTS ONLY — never eternal identity.
"""

import sqlite3

from michi.application.library_port import LibraryCatalogStorageError
from michi.infrastructure.library_catalog import validate_or_initialize_catalog


class SqliteLibraryMediaCache:
    """Rebuildable fingerprint/relocation cache in the MAIN database."""

    def __init__(self, db_path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        validate_or_initialize_catalog(conn)
        self._ensure_cache_table(conn)
        return conn

    @staticmethod
    def _ensure_cache_table(conn: sqlite3.Connection) -> None:
        # Rebuildable cache: missing table is created (never authoritative
        # identity — loss is recoverable by design).
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_media_cache ("
            "media_file_id TEXT PRIMARY KEY, "
            "file_size INTEGER NOT NULL, "
            "mtime_ns INTEGER NOT NULL, "
            "device_id INTEGER NOT NULL DEFAULT 0, "
            "inode INTEGER NOT NULL DEFAULT 0)"
        )

    def load_all(self) -> dict[str, tuple[int, int, int, int]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT media_file_id, file_size, mtime_ns, device_id, inode "
                "FROM library_media_cache"
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(f"media cache load failed: {exc}") from exc
        finally:
            conn.close()
        return {row[0]: (row[1], row[2], row[3], row[4]) for row in rows}

    def upsert(
        self,
        media_file_id: str,
        file_size: int,
        mtime_ns: int,
        device_id: int,
        inode: int,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO library_media_cache(media_file_id, file_size, "
                "mtime_ns, device_id, inode) VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(media_file_id) DO UPDATE SET "
                "file_size = excluded.file_size, mtime_ns = excluded.mtime_ns, "
                "device_id = excluded.device_id, inode = excluded.inode",
                (media_file_id, file_size, mtime_ns, device_id, inode),
            )
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"media cache write failed: {exc}"
            ) from exc
        finally:
            conn.close()

    def remove(self, media_file_id: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM library_media_cache WHERE media_file_id = ?",
                (media_file_id,),
            )
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"media cache remove failed: {exc}"
            ) from exc
        finally:
            conn.close()
