"""SQLite persistence for library preferences (favorites/history/recent)."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import LibraryPrefsPort
from michi.domain.library import LibraryPrefs

logger = logging.getLogger(__name__)

_PREFS_KEYS = ("favorites", "history", "recently_added")


class SqliteLibraryPrefsRepository(LibraryPrefsPort):
    """Key/value JSON rows in the shared settings database.

    Uses its own `library_prefs` table; never touches the settings table,
    never changes journal mode, never raises: persistence is best effort."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        return conn

    def load(self) -> LibraryPrefs:
        try:
            conn = self._connect()
            try:
                rows = dict(conn.execute("SELECT key, value FROM library_prefs"))
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("Library prefs load failed: %s", exc)
            return LibraryPrefs()
        return LibraryPrefs(
            favorite_paths=self._decode(rows.get("favorites")),
            history_paths=self._decode(rows.get("history")),
            recently_added_paths=self._decode(rows.get("recently_added")),
        )

    @staticmethod
    def _decode(raw):
        if not raw:
            return ()
        try:
            values = json.loads(raw)
        except ValueError:
            return ()
        return tuple(v for v in values if isinstance(v, str))

    def save(self, prefs: LibraryPrefs) -> None:
        payload = {
            "favorites": list(prefs.favorite_paths),
            "history": list(prefs.history_paths),
            "recently_added": list(prefs.recently_added_paths),
        }
        try:
            conn = self._connect()
            try:
                for key in _PREFS_KEYS:
                    conn.execute(
                        "INSERT INTO library_prefs(key, value) VALUES(?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, json.dumps(payload[key])),
                    )
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("Library prefs save failed: %s", exc)
