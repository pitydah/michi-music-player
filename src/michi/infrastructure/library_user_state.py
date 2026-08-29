"""Authoritative library user-state persistence by TrackId (M6-EXT-R4-G).

Favorites / history / recently-added move from best-effort JSON path lists
(library_prefs) to truthful TrackId collections in dedicated tables with
FK RESTRICT against the catalog. A write either commits or raises.

The tables are owned by the shared library-identity schema
(``validate_or_initialize_catalog``); this repository NEVER creates or
drops authoritative tables.
"""

import sqlite3

from michi.application.library_port import (
    LibraryCatalogStorageError,
    LibraryUserStatePort,
)


class SqliteLibraryUserStateRepository(LibraryUserStatePort):
    def __init__(self, db_path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        from michi.infrastructure.library_catalog import validate_or_initialize_catalog

        conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        validate_or_initialize_catalog(conn)
        return conn

    # ------------------------------------------------------------------ loads

    def load_favorites(self) -> tuple[str, ...]:
        return self._load_ordered("library_favorites", "track_id")

    def load_history(self) -> tuple[str, ...]:
        return self._load_ordered("library_history", "position")

    def load_recently_added(self) -> tuple[str, ...]:
        return self._load_ordered("library_recently_added", "position")

    def _load_ordered(self, table: str, order_column: str) -> tuple[str, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT track_id FROM {table} ORDER BY {order_column}"
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"library user state load failed ({table}): {exc}"
            ) from exc
        finally:
            conn.close()
        return tuple(row[0] for row in rows)

    # ------------------------------------------------------------------ writes

    def set_favorites(self, track_ids: tuple[str, ...]) -> None:
        self._replace("library_favorites", track_ids)

    def set_history(self, track_ids: tuple[str, ...]) -> None:
        self._replace("library_history", track_ids)

    def set_recently_added(self, track_ids: tuple[str, ...]) -> None:
        self._replace("library_recently_added", track_ids)

    def _replace(self, table: str, track_ids: tuple[str, ...]) -> None:
        """Atomically replace one user-state collection (one transaction).

        Favorites are stored in sorted order; history/recently-added store
        the application-provided order (position = list index).
        """
        order_column = "position" if table != "library_favorites" else "track_id"
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(f"DELETE FROM {table}")
            if table == "library_favorites":
                for track_id in sorted(track_ids):
                    conn.execute(
                        "INSERT INTO library_favorites(track_id) VALUES(?)",
                        (track_id,),
                    )
            else:
                for position, track_id in enumerate(track_ids):
                    conn.execute(
                        f"INSERT INTO {table}({order_column}, track_id) VALUES(?, ?)",
                        (position, track_id),
                    )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"library user state write failed ({table}): {exc}"
            ) from exc
        finally:
            conn.close()
