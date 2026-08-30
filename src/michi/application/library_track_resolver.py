"""ONE application authority for TrackId ↔ path/media resolution (M6-EXT-R4-J).

The resolver concentrates every stable-identity lookup so bridges, playlist
coordinators, history, queue and enrichment never spread path lookup code.

Path lookup answers remain DERIVED: the catalog TrackId is the identity;
``file_path`` is the current/last-known location projection.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from michi.application.library_port import LibraryCatalogPort
from michi.application.library_service import LibraryService
from michi.domain.library import TrackRef
from michi.domain.library_catalog import (
    MediaAvailability,
    MediaFileRecord,
    effective_availability,
)

logger = logging.getLogger(__name__)


class LibraryTrackResolver:
    """Application authority for track identity resolution.

    ``library`` is the live canonical model (TrackRefs); ``catalog`` is the
    optional authoritative catalog for media records.
    """

    def __init__(
        self,
        library: LibraryService,
        catalog: LibraryCatalogPort | None = None,
        source_availability_provider: "Callable[[str], object] | None" = None,
    ) -> None:
        self._library = library
        self._catalog = catalog
        self._source_availability_provider = source_availability_provider

    def effective_availability(self, ref: TrackRef) -> MediaAvailability:
        """Composed playability authority (M6-EXT-R4 freeze gate §11):
        source observation dominates, media observation otherwise — ONE
        composition, never duplicated in QML/Service."""
        if ref.library_source_id and self._source_availability_provider is not None:
            source = self._source_availability_provider(ref.library_source_id)
            return effective_availability(ref.availability, source)
        return ref.availability

    # ------------------------------------------------------------- by TrackId

    def resolve_ref(self, track_id: str) -> TrackRef | None:
        """Canonical TrackRef by stable identity, or None."""
        if not track_id:
            return None
        trackref_by_id = getattr(self._library, "trackref_by_id", None)
        if trackref_by_id is not None:
            ref = trackref_by_id(track_id)
            if ref is not None:
                return ref
        # LEGACY PATH-IDENTITY COMPATIBILITY: a ``legacy-path::<path>`` id
        # resolves through the current path projection.
        if track_id.startswith("legacy-path::"):
            return self._library.resolve_trackref(
                Path(track_id.removeprefix("legacy-path::"))
            )
        return None

    def resolve_media(self, track_id: str) -> MediaFileRecord | None:
        """Authoritative MediaFileRecord for a stable TrackId.

        Resolution chain: TrackId → TrackRecord → media_file_id →
        MediaFileRecord (never a media_id compared against a track_id)."""
        if self._catalog is None:
            return None
        track = self._catalog.get_track(track_id)
        if track is None:
            return None
        return self._catalog.get_media(track.media_file_id)

    def resolve_path(self, track_id: str) -> Path | None:
        """Current/last-known path projection, or None."""
        ref = self.resolve_ref(track_id)
        return ref.file_path if ref is not None else None

    def resolve_playable_path(self, track_id: str) -> Path | None:
        """Path only when the EFFECTIVE availability does not forbid
        playback (source observation + media observation composed).

        UNKNOWN (legacy records) remains playable-eligible — the filesystem
        gate (TD-013) still validates existence; explicit MISSING /
        SOURCE_OFFLINE / ACCESS_DENIED / IO_ERROR are not."""
        ref = self.resolve_ref(track_id)
        if ref is None:
            return None
        from michi.domain.library_catalog import media_playback_blocked

        if media_playback_blocked(self.effective_availability(ref)):
            return None
        return ref.file_path

    # -------------------------------------------------------------- by path

    def find_track_id_by_path(self, path: Path) -> str | None:
        """Stable TrackId for a current path (canonical id preferred; the
        documented legacy-path fallback is returned for pre-catalog
        records so callers never fabricate identity)."""
        ref = self._library.resolve_trackref(path)
        if ref is None:
            return None
        return ref.track_id or f"legacy-path::{ref.file_path}"
