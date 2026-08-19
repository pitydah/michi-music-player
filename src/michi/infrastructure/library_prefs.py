"""SQLite persistence for library preferences (favorites/history/recent)."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import LibraryPrefsPort
from michi.domain.library import LibraryPrefs

logger = logging.getLogger(__name__)

_PREFS_KEYS = ("favorites", "history", "recently_added")


def _decode_string_list(raw) -> tuple[tuple[str, ...], bool]:
    """STRICT string-list decode for AUTHORITATIVE user state.

    Returns ``(decoded, malformed)`` — the malformed flag is EXPLICIT so a
    VALID EMPTY list (``[]`` -> ``(), False``) is never confused with a
    malformed value (``42`` -> ``(), True``). The storage contract accepts
    ONLY SQLite TEXT: a non-str value (BLOB/number/float) is malformed.

    NEVER fabricate: a JSON string must never iterate into characters, a
    JSON object must never yield its keys as paths.
    NEVER partially salvage: ["A", 42, "B"] is malformed as a WHOLE -> (),
    not ("A", "B").

    Semantics: None -> (), False (missing row: normal absent state);
    "" -> (), True (empty string is not a valid persisted JSON document);
    "[]" -> (), False; '["A","B"]' -> ("A","B"), False; non-list roots,
    mixed lists and invalid JSON -> (), True.
    """
    if raw is None:
        return (), False
    if not isinstance(raw, str):
        return (), True  # strict TEXT contract: BLOB/number values are malformed
    if raw == "":
        return (), True
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return (), True
    if not isinstance(parsed, list):
        return (), True
    if not all(isinstance(item, str) for item in parsed):
        return (), True
    return tuple(parsed), False


class SqliteLibraryPrefsRepository(LibraryPrefsPort):
    """Key/value JSON rows in the shared settings database.

    Uses its own `library_prefs` table; never touches the settings table,
    never changes journal mode, never raises: persistence is best effort.
    Authoritative user state is decoded STRICTLY (safe empty fallback for
    malformed values — read tolerance, never repair)."""

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
            favorite_paths=self._decode("favorites", rows.get("favorites")),
            history_paths=self._decode("history", rows.get("history")),
            recently_added_paths=self._decode(
                "recently_added", rows.get("recently_added")
            ),
        )

    def _decode(self, key: str, raw) -> tuple[str, ...]:
        values, malformed = _decode_string_list(raw)
        if malformed:
            # Only REAL malformed persisted data warns: a valid empty list
            # and a missing row are normal state, never corruption.
            logger.warning(
                "Malformed library prefs value for %s; using safe empty fallback",
                key,
            )
        return values

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
