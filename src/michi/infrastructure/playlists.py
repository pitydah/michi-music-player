"""SQLite persistence for user playlists — shares the library_prefs table."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.domain.playlist import Playlist

logger = logging.getLogger(__name__)


class SqlitePlaylistsRepository(PlaylistsPort):
    """One JSON list under the 'playlists' key of the shared library_prefs
    table. Never touches the settings table or journal mode; never raises:
    persistence is best effort."""

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
            raw = json.loads(row[0])
        except ValueError:
            return ()
        playlists = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            paths = entry.get("track_paths")
            if isinstance(name, str) and isinstance(paths, list):
                playlists.append(
                    Playlist(name, tuple(p for p in paths if isinstance(p, str)))
                )
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
