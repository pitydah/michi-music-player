"""Playlist domain models (LOCAL-06 → M8-R1).

M8-R1 canonical rule: playlist identity is an immutable opaque id, fully
independent from the display name. Renaming never changes identity.
"""

import uuid
from dataclasses import dataclass

# Fixed namespace for deterministic legacy (V1) playlist ids (UUIDv5).
# Deliberately project-specific; never derived from user data beyond the
# stable input documented in legacy_playlist_id().
_MICHI_PLAYLIST_NAMESPACE = uuid.UUID("6f2a1b8e-4c3d-4a5b-9e8f-0a1b2c3d4e5f")

MAX_RECENT_PLAYLISTS = 5


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
class Playlist:
    """A user-defined persistent ordered collection of track paths.

    playlist_id is the canonical identity; name is mutable user-visible
    metadata. custom_cover_path is optional user-provided artwork."""

    playlist_id: str
    name: str
    track_paths: tuple[str, ...] = ()
    custom_cover_path: str = ""


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
