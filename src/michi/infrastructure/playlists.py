"""SQLite persistence for user playlists — shares the library_prefs table.

M8-R1: playlists persist with stable playlist ids. Persistence SHAPES
(M6-EXT-R4-H):

- V1 legacy: {"name", "track_paths"} → deterministic UUIDv5 id on decode.
- V2: {"id", "name", "track_paths"} — path-only membership (legacy).
- V3 (current emit shape): {"version": 3, "id", "name", "tracks":
  [{"track_id", "fallback_path"}], ...} — stable TrackId membership with a
  location snapshot.

Load never writes back. V1/V2 decoders remain (migration machinery + safe
read); production save emits V3 only.

Playlist navigation metadata (pinned/recent) persists under the
"playlist_navigation" key of the same table.
"""

import json
import logging
import math
import re
import sqlite3
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.domain.playlist import (
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
    PlaylistPersistenceError,
    legacy_playlist_id,
)

logger = logging.getLogger(__name__)

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# V3 payload marker. Historical V1/V2 payloads have no "version" member.
PLAYLIST_PERSISTENCE_VERSION = 3


def _decoded_color(value: object, fallback: str) -> str:
    if isinstance(value, str) and _HEX_COLOR.fullmatch(value.strip()):
        return value.strip().upper()
    return fallback


def _decode_appearance(value: object) -> PlaylistAppearance:
    """Tolerant field-by-field decode for optional appearance metadata.

    A missing/malformed appearance never invalidates the authoritative
    playlist record and never triggers writeback during load.
    """
    default = PlaylistAppearance()
    if not isinstance(value, dict):
        return default

    raw_mode = value.get("hero_mode")
    try:
        mode = PlaylistHeroMode(raw_mode)
    except (TypeError, ValueError):
        mode = PlaylistHeroMode.AUTO

    solid = _decoded_color(value.get("hero_solid_color"), default.hero_solid_color)

    raw_colors = value.get("hero_gradient_colors")
    colors = default.hero_gradient_colors
    if isinstance(raw_colors, list) and len(raw_colors) in (2, 3):
        decoded = tuple(_decoded_color(color, "") for color in raw_colors)
        if all(decoded):
            colors = decoded

    raw_angle = value.get("hero_gradient_angle")
    angle = default.hero_gradient_angle
    if (
        isinstance(raw_angle, (int, float))
        and not isinstance(raw_angle, bool)
        and math.isfinite(float(raw_angle))
    ):
        angle = float(raw_angle) % 360.0

    raw_image = value.get("hero_image_path")
    image_path = raw_image if isinstance(raw_image, str) else ""
    if mode is PlaylistHeroMode.IMAGE and not image_path:
        mode = PlaylistHeroMode.AUTO

    return PlaylistAppearance(
        hero_mode=mode,
        hero_solid_color=solid,
        hero_gradient_colors=colors,
        hero_gradient_angle=angle,
        hero_image_path=image_path,
    )


def _decode_playlist_entry(entry) -> Playlist | None:
    """STRICT playlist entry decode (authoritative user state), V1 + V2 + V3.

    Valid V3 shape: {"version": 3, "id": str, "name": str,
    "tracks": [{"track_id": str, "fallback_path": str}]}.
    Valid V2 shape: {"id": str, "name": str, "track_paths": list[str]}.
    Valid V1 shape: {"name": str, "track_paths": list[str]} — the id is
    derived deterministically via legacy_playlist_id(name).

    A malformed entry (non-dict, wrong member types, any non-string
    membership) is rejected WHOLE — NEVER partially salvaged. An explicitly
    persisted empty/wrong-typed id is treated as V1 (deterministic legacy
    derivation), never fabricated randomly. Valid sibling entries in the
    same root list are preserved (established best-effort collection
    semantics)."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        return None
    raw_id = entry.get("id")
    if isinstance(raw_id, str) and raw_id:
        playlist_id = raw_id
    else:
        # V1 record or empty/wrong-typed id: deterministic legacy identity.
        playlist_id = legacy_playlist_id(name)

    if entry.get("version") == PLAYLIST_PERSISTENCE_VERSION:
        track_ids, track_paths = _decode_v3_tracks(entry.get("tracks"))
    else:
        track_ids, track_paths = (), _decode_v2_paths(entry.get("track_paths"))
    if track_ids is None or track_paths is None:
        return None
    raw_cover = entry.get("custom_cover_path")
    custom_cover_path = raw_cover if isinstance(raw_cover, str) else ""
    appearance = _decode_appearance(entry.get("appearance"))
    return Playlist(
        playlist_id=playlist_id,
        name=name,
        track_ids=track_ids,
        track_paths=track_paths,
        custom_cover_path=custom_cover_path,
        appearance=appearance,
    )


def _decode_v2_paths(raw) -> tuple[str, ...] | None:
    """V1/V2 membership: a plain list of path strings."""
    if not isinstance(raw, list):
        return None
    if not all(isinstance(path, str) for path in raw):
        return None
    return tuple(raw)


def _decode_v3_tracks(raw) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
    """V3 membership: a list of {"track_id": str, "fallback_path": str}.

    Both collections must decode strictly; a missing track_id or a
    non-string fallback rejects the WHOLE playlist entry (never partially
    salvaged). All-empty collections normalize to () so a legacy path-only
    (or future id-only) record round-trips losslessly. Returns (None, None)
    on any violation."""
    if not isinstance(raw, list):
        return None, None
    track_ids: list[str] = []
    track_paths: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            return None, None
        track_id = item.get("track_id")
        fallback = item.get("fallback_path", "")
        if not isinstance(track_id, str):
            return None, None
        if not isinstance(fallback, str):
            return None, None
        track_ids.append(track_id)
        track_paths.append(fallback)
    normalized_ids = () if all(not i for i in track_ids) else tuple(track_ids)
    normalized_paths = () if all(not p for p in track_paths) else tuple(track_paths)
    return normalized_ids, normalized_paths


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
                "version": PLAYLIST_PERSISTENCE_VERSION,
                "id": p.playlist_id,
                "name": p.name,
                "tracks": [
                    {"track_id": ref.track_id, "fallback_path": ref.fallback_path}
                    for ref in p.references()
                ],
                # DERIVED COMPATIBILITY PROJECTION (never a second
                # authority): the location snapshot of the same membership,
                # kept so historical consumers of "track_paths" keep working.
                "track_paths": [ref.fallback_path for ref in p.references()],
                "custom_cover_path": p.custom_cover_path,
                "appearance": {
                    "hero_mode": p.appearance.hero_mode.value,
                    "hero_solid_color": p.appearance.hero_solid_color,
                    "hero_gradient_colors": list(p.appearance.hero_gradient_colors),
                    "hero_gradient_angle": p.appearance.hero_gradient_angle,
                    "hero_image_path": p.appearance.hero_image_path,
                },
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
        """TRUTHFUL authoritative write (M6-EXT-R4 freeze gate): a sqlite
        failure raises ``PlaylistPersistenceError`` — never a silent
        log-and-return. Load remains tolerant; writes are not."""
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
            raise PlaylistPersistenceError(
                f"playlist persistence failed ({key}): {exc}"
            ) from exc
