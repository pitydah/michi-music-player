"""SQLite persistence for user playlists — shares the library_prefs table."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.domain.playlist import Playlist

logger = logging.getLogger(__name__)


def _decode_playlist_entry(entry) -> Playlist | None:
    """STRICT playlist entry decode (authoritative user state).

    Valid shape: {"name": str, "track_paths": list[str]}. A malformed entry
    (non-dict, wrong member types, track_paths with ANY non-string member)
    is rejected WHOLE — NEVER partially salvaged (["A", 42] is malformed,
    not ["A"]). Valid sibling entries in the same root list are preserved
    (established best-effort collection semantics)."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    paths = entry.get("track_paths")
    if not isinstance(name, str) or not isinstance(paths, list):
        return None
    if not all(isinstance(path, str) for path in paths):
        return None
    return Playlist(name=name, track_paths=tuple(paths))


class SqlitePlaylistsRepository(PlaylistsPort):
    """One JSON list under the 'playlists' key of the shared library_prefs
    table. Never touches the settings table or journal mode; never raises:
    persistence is best effort.

    Malformed ROOT (scalar/string/object/null/boolean/invalid JSON) ->
    whole collection (). Malformed ENTRY -> that entry discarded; valid
    siblings preserved. No writeback during load (read tolerance, not
    repair)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        return conn

    def load(self) -> tuple[Playlist, ...]:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM library_prefs WHERE key = 'playlists'"
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("Playlists load failed: %s", exc)
            return ()
        if row is None:
            return ()
        try:
            parsed = json.loads(row[0])
        except (TypeError, ValueError):
            return ()
        if not isinstance(parsed, list):
            # Malformed ROOT: the whole persisted collection is rejected —
            # a scalar/string/object root can never fabricate playlists.
            logger.warning("Malformed playlists root; using safe empty fallback")
            return ()
        playlists = []
        for entry in parsed:
            playlist = _decode_playlist_entry(entry)
            if playlist is not None:
                playlists.append(playlist)
        return tuple(playlists)

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        payload = [
            {"name": p.name, "track_paths": list(p.track_paths)} for p in playlists
        ]
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO library_prefs(key, value) VALUES('playlists', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (json.dumps(payload),),
                )
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("Playlists save failed: %s", exc)
