"""SQLite persistence for user playlists — shares the library_prefs table.

M8-R1: playlists persist in V2 shape {"id", "name", "track_paths"}; legacy
V1 records {"name", "track_paths"} decode to a DETERMINISTIC UUIDv5 id
(domain.legacy_playlist_id) so restarts never change identity. Load never
writes back. Playlist navigation metadata (pinned/recent) persists under the
"playlist_navigation" key of the same table."""

import json
import logging
import math
import re
import sqlite3
from pathlib import Path

from michi.application.errors import PlaylistPersistenceError
from michi.application.ports import PlaylistsPort
from michi.domain.playlist import (
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
    legacy_playlist_id,
)

# PLAYLISTS POST-MERGE IDENTITY RECOVERY: production emits V3 ONLY.
#
# Historical shapes:
# - V1: {"name", "track_paths"} — path-only membership (legacy).
# - V2: {"id", "name", "track_paths"} — path-only membership (legacy).
# - V3 (current emit shape): {"version": 3, "id", "name", "tracks":
#   [{"track_id", "fallback_path"}], "track_paths": [...]} — stable TrackId
#   membership with a DERIVED path projection for historical consumers.
#
# Load never writes back. V1/V2 decoders remain (migration machinery + safe
# read); production save emits V3 only. A loaded V3 record is NEVER
# downgraded to V2 by a later save (the identity must survive resaves).
PLAYLIST_PERSISTENCE_VERSION = 3

logger = logging.getLogger(__name__)

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


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

    # PL-FINAL-09: focal point — tolerate missing fields, clamp malformed
    # values; no load-time writeback required.
    def _decoded_focal(key: str, fallback: float) -> float:
        raw = value.get(key)
        if (
            isinstance(raw, (int, float))
            and not isinstance(raw, bool)
            and math.isfinite(float(raw))
        ):
            return max(0.0, min(1.0, float(raw)))
        return fallback

    return PlaylistAppearance(
        hero_mode=mode,
        hero_solid_color=solid,
        hero_gradient_colors=colors,
        hero_gradient_angle=angle,
        hero_image_path=image_path,
        hero_focal_x=_decoded_focal("hero_focal_x", default.hero_focal_x),
        hero_focal_y=_decoded_focal("hero_focal_y", default.hero_focal_y),
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
    semantics). Load never writes back."""
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
    raw_description = entry.get("description")
    description = raw_description if isinstance(raw_description, str) else ""
    return Playlist(
        playlist_id=playlist_id,
        name=name,
        track_ids=track_ids,
        track_paths=track_paths,
        custom_cover_path=custom_cover_path,
        appearance=appearance,
        description=description,
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

    Both collections must decode strictly; a non-string track_id or
    fallback rejects the WHOLE playlist entry (never partially salvaged).
    All-empty collections normalize to () so a legacy path-only (or future
    id-only) record round-trips losslessly. Returns (None, None) on any
    violation."""
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
    journal mode; writes are authoritative (raise on failure).

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
        """AUTHORITATIVE WRITE (R2 P1-04): durable on success; raises
        PlaylistPersistenceError on any sqlite failure. Never best effort."""
        self._save_raw("playlists", json.dumps(self._payload(playlists)))

    def load_navigation(self) -> PlaylistNavigationState:
        parsed = self._load_raw("playlist_navigation")
        if parsed is None:
            return PlaylistNavigationState()
        return _decode_navigation_state(parsed)

    def save_navigation(self, state: PlaylistNavigationState) -> None:
        """AUTHORITATIVE WRITE (R2 P1-04): durable on success; raises
        PlaylistPersistenceError on any sqlite failure."""
        self._save_raw("playlist_navigation", _encode_navigation_state(state))

    def save_state(
        self,
        playlists: tuple[Playlist, ...],
        navigation: PlaylistNavigationState,
    ) -> None:
        """ATOMIC compound write (R2 P1-02): ONE connection, ONE
        transaction, TWO upserts, ONE commit. Any failure ROLLS BACK and
        raises PlaylistPersistenceError — there is NO observable moment
        where only one of the two authorities is confirmed."""
        try:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO library_prefs(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    ("playlists", json.dumps(self._payload(playlists))),
                )
                conn.execute(
                    "INSERT INTO library_prefs(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    ("playlist_navigation", _encode_navigation_state(navigation)),
                )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise PlaylistPersistenceError(
                f"playlist persistence failed (compound state): {exc}"
            ) from exc

    def _payload(self, playlists: tuple[Playlist, ...]) -> list[dict]:
        return _payload_for(playlists)

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
            # P0-02: TRUTHFUL persistence — a sqlite failure raises instead
            # of silently logging while QML reports success.
            raise PlaylistPersistenceError(
                f"playlist persistence failed ({key}): {exc}"
            ) from exc


def _payload_for(playlists: tuple[Playlist, ...]) -> list[dict]:
    """Canonical V3 write shape (production emit — never V2).

    ``tracks`` is the AUTHORITATIVE membership (stable TrackId +
    fallback location snapshot); ``track_paths`` is a DERIVED
    compatibility projection of the same membership, kept so historical
    path-based consumers keep working — never a second authority.
    ``version`` marks the shape so the loader can restore track_ids on
    the next read (a V3 record is never downgraded by a resave)."""
    return [
        {
            "version": PLAYLIST_PERSISTENCE_VERSION,
            "id": p.playlist_id,
            "name": p.name,
            "tracks": [
                {"track_id": ref.track_id, "fallback_path": ref.fallback_path}
                for ref in p.references()
            ],
            "track_paths": [ref.fallback_path for ref in p.references()],
            "custom_cover_path": p.custom_cover_path,
            "appearance": {
                "hero_mode": p.appearance.hero_mode.value,
                "hero_solid_color": p.appearance.hero_solid_color,
                "hero_gradient_colors": list(p.appearance.hero_gradient_colors),
                "hero_gradient_angle": p.appearance.hero_gradient_angle,
                "hero_image_path": p.appearance.hero_image_path,
                "hero_focal_x": p.appearance.hero_focal_x,
                "hero_focal_y": p.appearance.hero_focal_y,
            },
            "description": p.description,
        }
        for p in playlists
    ]
