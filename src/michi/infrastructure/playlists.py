"""SQLite persistence for user playlists — shares the library_prefs table.

M8-R1: playlists persist in V2 shape {"id", "name", "track_paths"}; legacy
V1 records {"name", "track_paths"} decode to a DETERMINISTIC UUIDv5 id
(domain.legacy_playlist_id) so restarts never change identity. Load never
writes back. Playlist navigation metadata (pinned/recent) persists under the
"playlist_navigation" key of the same table."""

import json
import logging
import sqlite3
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.domain.playlist import (
    Playlist,
    PlaylistNavigationState,
    legacy_playlist_id,
)

logger = logging.getLogger(__name__)


def _decode_playlist_entry(entry) -> Playlist | None:
    """STRICT playlist entry decode (authoritative user state), V1 + V2.

    Valid V2 shape: {"id": str, "name": str, "track_paths": list[str]}.
    Valid V1 shape: {"name": str, "track_paths": list[str]} — the id is
    derived deterministically via legacy_playlist_id(name).

    A malformed entry (non-dict, wrong member types, track_paths with ANY
    non-string member, empty name) is rejected WHOLE — NEVER partially
    salvaged. An explicitly persisted empty/wrong-typed id is treated as V1
    (deterministic legacy derivation), never fabricated randomly. Valid
    sibling entries in the same root list are preserved (established
    best-effort collection semantics)."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    paths = entry.get("track_paths")
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(paths, list):
        return None
    if not all(isinstance(path, str) for path in paths):
        return None
    raw_id = entry.get("id")
    if isinstance(raw_id, str) and raw_id:
        playlist_id = raw_id
    else:
        # V1 record or empty/wrong-typed id: deterministic legacy identity.
        playlist_id = legacy_playlist_id(name)
    return Playlist(playlist_id=playlist_id, name=name, track_paths=tuple(paths))


def _decode_navigation_state(value: object) -> PlaylistNavigationState:
    """STRICT decode of the playlist_navigation payload.

    Valid shape: {"pinned_ids": [str...], "recent_ids": [str...]}. Any
    malformed member is dropped; ids must be non-empty strings. Never
    raises; malformed payloads degrade to the empty state. No writeback
    during load (read tolerance, not repair)."""
    if not isinstance(value, dict):
        return PlaylistNavigationState()
    pinned, recent = (), ()
    for key in ("pinned_ids", "recent_ids"):
        raw = value.get(key)
        if not isinstance(raw, list):
            continue
        ids = tuple(i for i in raw if isinstance(i, str) and i)
        if key == "pinned_ids":
            pinned = ids
        else:
            recent = ids
    return PlaylistNavigationState(pinned_ids=pinned, recent_ids=recent)


def _encode_navigation_state(state: PlaylistNavigationState) -> str:
    return json.dumps(
        {"pinned_ids": list(state.pinned_ids), "recent_ids": list(state.recent_ids)}
    )


class SqlitePlaylistsRepository(PlaylistsPort):
    """JSON payloads under the 'playlists' and 'playlist_navigation' keys of
    the shared library_prefs table. Never touches the settings table or
    journal mode; never raises: persistence is best effort.

    Malformed ROOT (scalar/string/object/null/boolean/invalid JSON) ->
    whole collection (). Malformed ENTRY -> that entry discarded; valid
    siblings preserved. Duplicate ids -> first valid occurrence wins, later
    duplicates dropped. No writeback during load (read tolerance, not
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

    def _load_raw(self, key: str):
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM library_prefs WHERE key = ?", (key,)
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("%s load failed: %s", key, exc)
            return None
        if row is None:
            return None
        raw = row[0]
        if not isinstance(raw, str):
            # Strict TEXT contract (M6-FINAL-DECODE-LOGGING-MICROFIX): a
            # non-text SQLite value (BLOB/number) is malformed, never
            # decoded as if it were JSON text.
            logger.warning("Malformed %s root; using safe empty fallback", key)
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Malformed %s root; using safe empty fallback", key)
            return None

    def load(self) -> tuple[Playlist, ...]:
        parsed = self._load_raw("playlists")
        if parsed is None:
            return ()
        if not isinstance(parsed, list):
            # Malformed ROOT: the whole persisted collection is rejected —
            # a scalar/string/object root can never fabricate playlists.
            logger.warning("Malformed playlists root; using safe empty fallback")
            return ()
        playlists = []
        seen_ids: set[str] = set()
        for entry in parsed:
            playlist = _decode_playlist_entry(entry)
            if playlist is None:
                continue
            if playlist.playlist_id in seen_ids:
                # Duplicate id: first valid occurrence wins; the later
                # duplicate is dropped (never merged, never invented).
                logger.warning(
                    "Duplicate playlist id dropped: %s", playlist.playlist_id
                )
                continue
            seen_ids.add(playlist.playlist_id)
            playlists.append(playlist)
        return tuple(playlists)

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        payload = [
            {
                "id": p.playlist_id,
                "name": p.name,
                "track_paths": list(p.track_paths),
            }
            for p in playlists
        ]
        self._save_raw("playlists", json.dumps(payload))

    def load_navigation(self) -> PlaylistNavigationState:
        parsed = self._load_raw("playlist_navigation")
        if parsed is None:
            return PlaylistNavigationState()
        return _decode_navigation_state(parsed)

    def save_navigation(self, state: PlaylistNavigationState) -> None:
        self._save_raw("playlist_navigation", _encode_navigation_state(state))

    def _save_raw(self, key: str, payload: str) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO library_prefs(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, payload),
                )
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("%s save failed: %s", key, exc)
