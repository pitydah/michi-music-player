"""Playlist domain models (LOCAL-06 → M8-R1).

M8-R1 canonical rule: playlist identity is an immutable opaque id, fully
independent from the display name. Renaming never changes identity.
"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

# Fixed namespace for deterministic legacy (V1) playlist ids (UUIDv5).
# Deliberately project-specific; never derived from user data beyond the
# stable input documented in legacy_playlist_id().
_MICHI_PLAYLIST_NAMESPACE = uuid.UUID("6f2a1b8e-4c3d-4a5b-9e8f-0a1b2c3d4e5f")

MAX_RECENT_PLAYLISTS = 5
MAX_DESCRIPTION_LENGTH = 1000


class PlaylistPersistenceError(RuntimeError):
    """An authoritative playlist write failed (M6-EXT-R4 freeze gate).

    Truthful persistence: a mutation either commits or raises — the
    in-memory state rolls back to the last persisted snapshot and the
    caller never sees a false success."""


class PlaylistHeroMode(StrEnum):
    """Persisted visual source for an individual playlist hero."""

    AUTO = "auto"
    SOLID = "solid"
    GRADIENT = "gradient"
    IMAGE = "image"


@dataclass(frozen=True)
class PlaylistAppearance:
    """User-owned, persistent hero appearance metadata.

    Cover artwork intentionally remains a separate ``Playlist`` field:
    resetting or replacing either visual must never mutate the other.
    Defaults are usable values even when ``hero_mode`` is ``AUTO`` so a
    mode switch never exposes incomplete presentation state.
    """

    hero_mode: PlaylistHeroMode = PlaylistHeroMode.AUTO
    hero_solid_color: str = "#152A45"
    hero_gradient_colors: tuple[str, ...] = ("#152A45", "#13243D")
    hero_gradient_angle: float = 135.0
    hero_image_path: str = ""
    # PL-FINAL-09: focal point of the hero IMAGE (0..1 normalized; the
    # default 0.5/0.5 is the exact backward-compatible center crop).
    hero_focal_x: float = 0.5
    hero_focal_y: float = 0.5


def legacy_playlist_id(name: str) -> str:
    """Deterministic identity for a legacy V1 playlist record.

    V1 records have no persisted id. Deriving a UUIDv5 from the normalized
    original persisted name gives the SAME id on every load/restart, so
    pinned/recent/navigation references survive migration. Name is used ONLY
    for deterministic migration of legacy records; new playlists get fresh
    UUID4 ids and identity becomes fully name-independent after the first
    legitimate persistence."""
    return str(uuid.uuid5(_MICHI_PLAYLIST_NAMESPACE, f"legacy_playlist::{name}"))


def new_playlist_id() -> str:
    """Fresh collision-resistant opaque identity (UUID4, canonical str)."""
    return str(uuid.uuid4())


@dataclass(frozen=True)
class PlaylistTrackReference:
    """One playlist membership intent (M6-EXT-R4-H).

    ``track_id`` is the CANONICAL library identity; ``fallback_path`` is a
    location snapshot used only while the catalog resolves (never identity).
    """

    track_id: str = ""
    fallback_path: str = ""


@dataclass(frozen=True)
class Playlist:
    """A user-defined persistent ordered collection of tracks.

    playlist_id is the canonical identity; name is mutable user-visible
    metadata. custom_cover_path and appearance are independent user-owned
    visual metadata.

    Track membership (M6-EXT-R4-H):
    - ``track_ids`` is the CANONICAL NEW AUTHORITY (stable library identity).
    - ``track_paths`` is the LEGACY/FALLBACK location snapshot — NEVER
      identity. New production records keep both aligned by position;
      legacy V1/V2 records may carry only ``track_paths`` until migration
      resolves their ids.
    """

    playlist_id: str
    name: str
    # Field order is a compatibility seam: legacy code constructs
    # ``Playlist(id, name, paths)`` positionally — track_paths keeps its
    # historical slot (third). New production code uses keyword arguments.
    track_paths: tuple[str, ...] = ()
    track_ids: tuple[str, ...] = ()
    custom_cover_path: str = ""
    appearance: PlaylistAppearance = field(default_factory=PlaylistAppearance)
    # PL-FINAL-05: playlist metadata (NOT appearance) — survives rename,
    # track mutation and appearance changes; "" means no description.
    description: str = ""

    def references(self) -> tuple[PlaylistTrackReference, ...]:
        """Position-aligned membership references.

        Aligns ``track_ids`` and ``track_paths`` by index; whenever only one
        collection is populated (legacy path-only or id-only records) the
        other side stays empty per entry.
        """
        count = max(len(self.track_ids), len(self.track_paths))
        ids = self.track_ids
        paths = self.track_paths
        return tuple(
            PlaylistTrackReference(
                track_id=ids[i] if i < len(ids) else "",
                fallback_path=paths[i] if i < len(paths) else "",
            )
            for i in range(count)
        )


@dataclass(frozen=True)
class PlaylistNavigationState:
    """Pinned / recent playlist navigation metadata.

    Both collections reference playlist ids — never names. Immutable
    replacement semantics: mutate by constructing a new instance."""

    pinned_ids: tuple[str, ...] = ()
    recent_ids: tuple[str, ...] = ()


def normalize_navigation_state(
    state: PlaylistNavigationState, valid_ids: tuple[str, ...]
) -> PlaylistNavigationState:
    """SAFE READ normalization of persisted navigation metadata against the
    actual playlist collection (M8-R1F).

    - Preserves the persisted order (no artificial reordering).
    - Removes ids not present in valid_ids (stale references).
    - Removes duplicates, keeping the FIRST occurrence.
    - Truncates recent_ids to MAX_RECENT_PLAYLISTS.

    Pure function: never writes back; callers persist only on the next
    legitimate navigation metadata mutation."""

    def normalized(ids: tuple[str, ...]) -> tuple[str, ...]:
        result = []
        seen: set[str] = set()  # dedupe is per-list (pinned and recent are
        # independent collections; an id may validly appear in both)
        for playlist_id in ids:
            if playlist_id in seen:
                continue  # duplicate: first occurrence wins
            if playlist_id not in valid_ids:
                continue  # stale: references a playlist that no longer exists
            seen.add(playlist_id)
            result.append(playlist_id)
        return tuple(result)

    pinned = normalized(state.pinned_ids)
    recent = normalized(state.recent_ids)
    recent = recent[:MAX_RECENT_PLAYLISTS]
    return PlaylistNavigationState(pinned_ids=pinned, recent_ids=recent)
