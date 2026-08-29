"""Library catalog domain — stable identity model (M6-EXT-R4).

Separates the three durable identities the Library must stop conflating:

    LibrarySourceId — user-configured storage root.
    MediaFileId     — physical audio object (one file, one record).
    TrackId         — durable logical music identity (move/rename/retag/
                      re-encode preserve it; CUE later maps 1 media → N tracks).

PATH IS LOCATION ONLY. It is never identity here.

New entities: UUID4 once, persisted forever.
Legacy migration: deterministic UUIDv5 from fixed project namespaces — that
machinery is migration-only and MUST NOT become the ID algorithm for future
scanned tracks (see ``legacy_*_id`` docstrings).
"""

import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import NewType

# Semantic identity aliases. Plain str at runtime (no Qt serialization
# friction); the distinct names keep the concepts unambiguous.
LibrarySourceId = NewType("LibrarySourceId", str)
MediaFileId = NewType("MediaFileId", str)
TrackId = NewType("TrackId", str)

# ---------------------------------------------------------------------------
# Fixed project namespaces for deterministic legacy identity derivation.
# Pinned here forever: re-deriving legacy ids after a namespace change would
# split every migrated user reference.
# ---------------------------------------------------------------------------
_MICHI_LEGACY_SOURCE_NS = uuid.UUID("3c9d1b4e-8f2a-4c6d-9e01-2b7a3c4d5e6f")
_MICHI_LEGACY_MEDIA_NS = uuid.UUID("7a4e2f3c-1b9d-4e5a-8c6f-0d1e2f3a4b5c")
_MICHI_LEGACY_TRACK_NS = uuid.UUID("5b1a6d2e-3c4f-4a7b-9e8d-1f2a3b4c5d6e")


def new_library_source_id() -> LibrarySourceId:
    """Fresh collision-resistant source identity (UUID4, canonical str)."""
    return LibrarySourceId(str(uuid.uuid4()))


def new_media_file_id() -> MediaFileId:
    """Fresh collision-resistant media identity (UUID4, canonical str)."""
    return MediaFileId(str(uuid.uuid4()))


def new_track_id() -> TrackId:
    """Fresh collision-resistant track identity (UUID4, canonical str)."""
    return TrackId(str(uuid.uuid4()))


def legacy_source_id(root_path: str) -> LibrarySourceId:
    """Deterministic source identity for a LEGACY root path.

    MIGRATION MACHINERY ONLY. New sources always use ``new_library_source_id``.
    """
    canonical = str(uuid.uuid5(_MICHI_LEGACY_SOURCE_NS, f"legacy-source::{root_path}"))
    return LibrarySourceId(canonical)


def legacy_media_id(file_path: str) -> MediaFileId:
    """Deterministic media identity for a LEGACY file path.

    MIGRATION MACHINERY ONLY. New media always use ``new_media_file_id``.
    """
    canonical = str(uuid.uuid5(_MICHI_LEGACY_MEDIA_NS, f"legacy-media::{file_path}"))
    return MediaFileId(canonical)


def legacy_track_id(file_path: str) -> TrackId:
    """Deterministic track identity for a LEGACY file path.

    MIGRATION MACHINERY ONLY. New tracks always use ``new_track_id``.
    """
    canonical = str(uuid.uuid5(_MICHI_LEGACY_TRACK_NS, f"legacy-track::{file_path}"))
    return TrackId(canonical)


class SourceLifecycle(StrEnum):
    """Persisted lifecycle of a configured library source.

    Lifecycle is durable user state. ``RETIRED`` ("remove from Michi")
    excludes the source from active projections while preserving every
    catalog record and user reference — never a filesystem or cascade delete.
    """

    ACTIVE = "active"
    RETIRED = "retired"


class SourceAvailability(StrEnum):
    """OBSERVED source availability — an observation, never eternal truth.

    On restart the cached availability is only UI history; the source is
    re-probed asynchronously/explicitly before a scan is attempted.
    """

    UNKNOWN = "unknown"
    AVAILABLE = "available"
    OFFLINE = "offline"
    MISSING_ROOT = "missing_root"
    ACCESS_DENIED = "access_denied"
    IO_ERROR = "io_error"
    DISABLED = "disabled"


class MediaAvailability(StrEnum):
    """OBSERVED media availability. A non-empty path never implies playable;
    availability determines playability."""

    UNKNOWN = "unknown"
    AVAILABLE = "available"
    MISSING = "missing"
    SOURCE_OFFLINE = "source_offline"
    ACCESS_DENIED = "access_denied"
    IO_ERROR = "io_error"


def effective_availability(
    media: MediaAvailability, source: SourceAvailability
) -> MediaAvailability:
    """THE single composition authority for effective playability
    (M6-EXT-R4 freeze gate §11).

    A source-level observation (offline / missing root / access denied /
    I/O error / disabled) dominates the per-media observation WITHOUT any
    per-child write storm: an offline NAS makes every child effectively
    unplayable while their stored media availability stays untouched. An
    available source defers to the media observation.
    """
    if source in (
        SourceAvailability.OFFLINE,
        SourceAvailability.MISSING_ROOT,
        SourceAvailability.DISABLED,
    ):
        return MediaAvailability.SOURCE_OFFLINE
    if source is SourceAvailability.ACCESS_DENIED:
        return MediaAvailability.ACCESS_DENIED
    if source is SourceAvailability.IO_ERROR:
        return MediaAvailability.IO_ERROR
    return media


@dataclass(frozen=True)
class LibrarySource:
    """A user-configured storage root (authoritative catalog record)."""

    library_source_id: LibrarySourceId
    display_name: str
    root_path: str
    enabled: bool = True
    lifecycle: SourceLifecycle = SourceLifecycle.ACTIVE


@dataclass(frozen=True)
class MediaFileRecord:
    """One physical audio object (authoritative catalog record).

    ``library_source_id``/``relative_path`` are None ONLY for unresolved
    legacy/orphan media (no trusted source root); ``last_known_path`` is
    diagnostic/fallback — NEVER canonical identity.
    """

    media_file_id: MediaFileId
    library_source_id: LibrarySourceId | None
    relative_path: str | None
    last_known_path: str
    availability: MediaAvailability = MediaAvailability.UNKNOWN


@dataclass(frozen=True)
class TrackRecord:
    """Durable logical music identity binding (authoritative catalog record).

    Deliberately metadata-free: codec/title/artist/year are cache metadata,
    NOT durable identity. One media file may own many tracks (CUE, R7).
    """

    track_id: TrackId
    media_file_id: MediaFileId
    created_at_ms: int = 0


def validate_relative_media_path(raw: str) -> str:
    """Validate a user/legacy-supplied relative media path inside a source.

    Rejects absolute paths, ``..`` escapes and empty paths; returns the
    canonical POSIX-normalized relative path. Path is location only — the
    validation guarantees it cannot escape its LibrarySource.
    """
    path = PurePosixPath(raw)

    if path.is_absolute():
        raise ValueError("relative media path must not be absolute")

    if ".." in path.parts:
        raise ValueError("relative media path escapes source")

    if not path.parts:
        raise ValueError("relative media path must not be empty")

    return path.as_posix()
