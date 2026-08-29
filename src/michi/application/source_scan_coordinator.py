"""Source-aware scan coordinator (M6-EXT-R4-K/L).

ONE serialized per-source scan authority:

- Source A scan mutates ONLY Source A (canonical Library = union of the
  active source catalogs).
- The source root is probed BEFORE enumeration: an offline source yields ONE
  source-level state and ZERO child MISSING rows.
- A known media file that disappeared while its source is AVAILABLE is
  marked MISSING — never deleted, identity preserved.
- A fingerprint change is MODIFIED (same MediaFileId/TrackId; metadata
  re-extracted) — never a new identity.
- A same-source move is relinked ONLY when unambiguous: old media MISSING +
  exactly ONE new candidate with the same (device, inode) observation. No
  contradiction → otherwise a NEW identity (ADDED).
- Catalog writes are authoritative: any catalog failure → FAILED outcome,
  no state publication, no COMPLETED.
- The physical fingerprint cache is REBUILDABLE evidence — never identity.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from michi.application.library_port import (
    DiscoveredMediaFile,
    LibraryCatalogError,
    LibraryCatalogPort,
    LibraryFilesystemError,
    LibrarySourceScannerPort,
)
from michi.application.library_service import LibraryService
from michi.application.ports import MetadataExtractorPort
from michi.domain.library import TrackMetadata, TrackRef
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceAvailability,
    TrackRecord,
    new_media_file_id,
    new_track_id,
)

logger = logging.getLogger(__name__)


class TrackScanDelta(StrEnum):
    """Per-file reconciliation outcome (R4-K/L)."""

    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    RELINKED = "relinked"
    MISSING = "missing"
    SOURCE_OFFLINE = "source_offline"


@dataclass(frozen=True)
class SourceScanOutcome:
    """Truthful per-source scan outcome."""

    source_id: str
    availability: SourceAvailability
    unchanged: int = 0
    modified: int = 0
    added: int = 0
    relinked: int = 0
    missing: int = 0
    failed: bool = False
    diagnostic: str = ""

    @property
    def total(self) -> int:
        return self.unchanged + self.modified + self.added + self.relinked


class SourceScanCoordinator:
    """Serialized per-source reconciliation. Discovery + extraction run on
    the calling thread; the catalog commit is authoritative and synchronous;
    a catalog failure aborts BEFORE any state publication."""

    def __init__(
        self,
        library: LibraryService,
        catalog: LibraryCatalogPort,
        scanner: LibrarySourceScannerPort,
        media_cache=None,
        metadata_extractor: MetadataExtractorPort | None = None,
        index=None,
    ) -> None:
        self._library = library
        self._catalog = catalog
        self._scanner = scanner
        self._media_cache = media_cache
        self._metadata_extractor = metadata_extractor
        self._index = index
        self._observations: dict[str, SourceAvailability] = {}

    # ------------------------------------------------------------ hydration

    def hydrate_catalog(self) -> int:
        """STARTUP CACHED LIBRARY (M6-EXT-R4 §55): load the catalog + media
        cache into LibraryState WITHOUT any scan — a disconnected NAS still
        renders its previously indexed music (identity, cached metadata,
        availability), and M7 search finds it.

        Metadata comes from the rebuildable index cache (path-keyed) when
        available; otherwise the ref carries identity + availability with an
        honest title from the last-known path. Returns the hydrated track
        count. Availability is the last OBSERVED state (UI history, re-probed
        on the next scan)."""
        media_by_id = {m.media_file_id: m for m in self._catalog.load_media()}
        track_by_id = {t.media_file_id: t for t in self._catalog.load_tracks()}
        cache = (
            {Path(path): meta for path, meta in self._index_metadata().items()}
            if self._index is not None
            else {}
        )
        refs: list[TrackRef] = []
        for media in media_by_id.values():
            track = track_by_id.get(media.media_file_id)
            path = Path(media.last_known_path)
            meta = cache.get(path)
            if track is not None and meta is not None:
                ref = self._library._trackref_from_metadata(
                    path,
                    meta,
                    track_id=track.track_id,
                    media_file_id=media.media_file_id,
                    library_source_id=media.library_source_id or "",
                )
            else:
                ref = TrackRef(
                    file_path=path,
                    display_name=path.stem,
                    title=path.stem,
                    track_id=track.track_id if track is not None else "",
                    media_file_id=media.media_file_id,
                    library_source_id=media.library_source_id or "",
                )
            from dataclasses import replace

            ref = replace(ref, availability=media.availability)
            refs.append(ref)

        # Hydration is the FULL catalog projection (startup cached library):
        # replace the state wholesale; later per-source scans reconcile each
        # source independently. No recently-added changes (not new).
        self._library._state.tracks = refs
        self._library._rebuild_derived_library_state()
        self._library._notify()
        return len(refs)

    def _index_metadata(self) -> dict:
        if self._index is None:
            return {}
        try:
            return {entry.track_id: entry.metadata for entry in self._index.load_all()}
        except Exception as exc:  # cache is rebuildable: never fatal
            logger.warning("index cache read failed during hydration: %s", exc)
            return {}

    # ------------------------------------------------------------ observables

    def observed_availability(self, source_id: str) -> SourceAvailability:
        """Last OBSERVED source availability (UI history, never eternal
        truth — re-probed on every scan)."""
        return self._observations.get(source_id, SourceAvailability.UNKNOWN)

    # ------------------------------------------------------------------ scan

    def scan_source(self, source: LibrarySource) -> SourceScanOutcome:
        """Reconcile ONE source against its catalog records.

        RETIRED/disabled sources are skipped entirely (no writes)."""
        if source.lifecycle.value == "retired" or not source.enabled:
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=SourceAvailability.DISABLED,
            )

        try:
            discovered = self._scanner.discover(source)
        except LibraryFilesystemError as exc:
            availability = _availability_from_code(exc.code)
            self._observations[source.library_source_id] = availability
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=availability,
                diagnostic=exc.detail or exc.code.value,
            )

        self._observations[source.library_source_id] = SourceAvailability.AVAILABLE
        return self._reconcile_available(source, discovered)

    def _reconcile_available(
        self,
        source: LibrarySource,
        discovered: tuple[DiscoveredMediaFile, ...],
    ) -> SourceScanOutcome:
        known_by_path = {
            media.relative_path: media
            for media in self._catalog.media_for_source(source.library_source_id)
        }
        track_by_media = {
            track.media_file_id: track for track in self._catalog.load_tracks()
        }
        cache = self._media_cache.load_all() if self._media_cache is not None else {}
        index_meta = (
            {entry.track_id: entry.metadata for entry in self._index.load_all()}
            if self._index is not None
            else {}
        )

        outcome = SourceScanOutcome(
            source_id=source.library_source_id,
            availability=SourceAvailability.AVAILABLE,
        )
        refs: list[TrackRef] = []
        upsert_media: list[MediaFileRecord] = []
        upsert_tracks: list[TrackRecord] = []
        new_track_ids: list[str] = []
        seen_paths: set[str] = {item.relative_path for item in discovered}

        # PHASE 1 — in-memory missing marking: known media not discovered
        # while the source is AVAILABLE become MISSING (identity preserved).
        # The relink candidate set is built FROM these fresh MISSING
        # records, so a just-moved file relinks in the SAME scan.
        missing_updates: dict[str, MediaFileRecord] = {}
        for relative, media in known_by_path.items():
            if relative not in seen_paths:
                missing_updates[media.media_file_id] = MediaFileRecord(
                    media_file_id=media.media_file_id,
                    library_source_id=media.library_source_id,
                    relative_path=media.relative_path,
                    last_known_path=media.last_known_path,
                    availability=MediaAvailability.MISSING,
                )

        # PHASE 2 — bounded relink candidates: fresh-MISSING media with a
        # unique cached (device_id, inode) observation.
        relink_candidates: dict[tuple[int, int], MediaFileRecord] = {}
        for media in missing_updates.values():
            cached = cache.get(media.media_file_id)
            if cached is None or not cached[2] or not cached[3]:
                continue  # no usable relocation evidence
            key = (cached[2], cached[3])
            if key not in relink_candidates:
                relink_candidates[key] = media

        # PHASE 3 — discovered items reconcile against known/missing state.
        index_upserts: list[_IndexEntry] = []
        for item in discovered:
            known = known_by_path.get(item.relative_path)
            media_id: str
            track: TrackRecord | None

            if known is not None:
                # CASE A: same relative location → same identities.
                media_id = known.media_file_id
                track = track_by_media.get(media_id)
                if media_id in missing_updates:
                    upsert_media.append(
                        _media_available(missing_updates[media_id], item)
                    )
                    outcome = _bump(outcome, TrackScanDelta.RELINKED)
                else:
                    cached = cache.get(media_id)
                    if (
                        cached is not None
                        and cached[0] == item.file_size
                        and cached[1] == item.mtime_ns
                    ):
                        outcome = _bump(outcome, TrackScanDelta.UNCHANGED)
                    else:
                        outcome = _bump(outcome, TrackScanDelta.MODIFIED)
            else:
                # CASE B: new relative path → bounded relink candidate.
                key = (item.device_id, item.inode)
                candidate = relink_candidates.get(key)
                if candidate is not None and item.device_id and item.inode:
                    # EXACT unique same-source move: preserve identities.
                    media_id = candidate.media_file_id
                    track = track_by_media.get(media_id)
                    upsert_media.append(_media_available(candidate, item))
                    # The relinked media is no longer missing.
                    missing_updates.pop(media_id, None)
                    outcome = _bump(outcome, TrackScanDelta.RELINKED)
                else:
                    # NEW identity (authoritative only after catalog commit).
                    media_id = new_media_file_id()
                    track_id = new_track_id()
                    track = TrackRecord(track_id=track_id, media_file_id=media_id)
                    upsert_media.append(
                        MediaFileRecord(
                            media_file_id=media_id,
                            library_source_id=source.library_source_id,
                            relative_path=item.relative_path,
                            last_known_path=str(item.absolute_path),
                            availability=MediaAvailability.AVAILABLE,
                        )
                    )
                    upsert_tracks.append(track)
                    new_track_ids.append(track_id)
                    outcome = _bump(outcome, TrackScanDelta.ADDED)

            # Metadata: reuse the rebuildable index cache for UNCHANGED
            # (zero extraction); extract otherwise and refresh the cache.
            meta = index_meta.get(str(item.absolute_path))
            if meta is None:
                meta = self._extract_meta(item.absolute_path)
                index_upserts.append(
                    _IndexEntry(
                        str(item.absolute_path),
                        item.file_size,
                        item.mtime_ns,
                        meta,
                    )
                )

            refs.append(
                self._build_ref(
                    item.absolute_path,
                    meta=meta,
                    media_id=media_id,
                    track=track,
                    source_id=source.library_source_id,
                    availability=MediaAvailability.AVAILABLE,
                )
            )
            if self._media_cache is not None:
                self._media_cache.upsert(
                    media_id,
                    item.file_size,
                    item.mtime_ns,
                    item.device_id,
                    item.inode,
                )

        # PHASE 4 — persist the fresh MISSING records and project them.
        for media in missing_updates.values():
            upsert_media.append(media)
            outcome = _bump(outcome, TrackScanDelta.MISSING)
            refs.append(
                self._build_ref(
                    Path(media.last_known_path),
                    meta=index_meta.get(media.last_known_path),
                    media_id=media.media_file_id,
                    track=track_by_media.get(media.media_file_id),
                    source_id=source.library_source_id,
                    availability=MediaAvailability.MISSING,
                )
            )

        # Authoritative commit BEFORE any state publication.
        try:
            self._catalog.upsert_media(tuple(upsert_media))
            self._catalog.upsert_tracks(tuple(upsert_tracks))
            if self._index is not None and index_upserts:
                # Rebuildable cache: refreshed AFTER the authoritative
                # commit (a failed catalog write never advances the cache).
                self._index.upsert_many(tuple(index_upserts))
        except LibraryCatalogError as exc:
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=SourceAvailability.AVAILABLE,
                failed=True,
                diagnostic=f"catalog commit failed: {exc}",
            )

        # Publish ONLY after the durable commit succeeded; recently-added is
        # recorded AFTER publication so the new ids resolve to their paths.
        self._library.apply_source_tracks(source.library_source_id, refs)
        if new_track_ids:
            self._library.note_new_track_ids(tuple(new_track_ids))
        return outcome

    def _extract_meta(self, path: Path) -> TrackMetadata:
        if self._metadata_extractor is None:
            return TrackMetadata(title=path.stem)
        try:
            return self._metadata_extractor.extract(path)
        except Exception as exc:  # extractor contract never raises, seal
            logger.warning("metadata extraction failed for %s: %s", path, exc)
            return TrackMetadata(title=path.stem)

    def _build_ref(
        self,
        path: Path,
        *,
        meta: TrackMetadata | None,
        media_id: str,
        track: TrackRecord | None,
        source_id: str,
        availability: MediaAvailability = MediaAvailability.AVAILABLE,
    ) -> TrackRef:
        if track is None:
            return TrackRef(
                file_path=path,
                display_name=path.stem,
                title=path.stem,
                track_id="",
                media_file_id=media_id,
                library_source_id=source_id,
                availability=availability,
            )
        meta = meta or self._extract_meta(path)
        from dataclasses import replace

        return replace(
            self._library._trackref_from_metadata(
                path,
                meta,
                track_id=track.track_id,
                media_file_id=media_id,
                library_source_id=source_id,
            ),
            availability=availability,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _IndexEntry:
    """Path-keyed rebuildable metadata cache entry (index repo shape)."""

    def __init__(self, track_id: str, file_size: int, mtime_ns: int, metadata) -> None:
        self.track_id = track_id
        self.file_size = file_size
        self.mtime_ns = mtime_ns
        self.metadata = metadata


def _availability_from_code(code) -> SourceAvailability:
    from michi.domain.library import LibraryDiagnosticCode

    mapping = {
        LibraryDiagnosticCode.DIRECTORY_MISSING: SourceAvailability.MISSING_ROOT,
        LibraryDiagnosticCode.ACCESS_FAILURE: SourceAvailability.ACCESS_DENIED,
        LibraryDiagnosticCode.IO_FAILURE: SourceAvailability.IO_ERROR,
    }
    return mapping.get(code, SourceAvailability.OFFLINE)


def _media_available(
    record: MediaFileRecord, item: DiscoveredMediaFile
) -> MediaFileRecord:
    return MediaFileRecord(
        media_file_id=record.media_file_id,
        library_source_id=record.library_source_id,
        relative_path=item.relative_path,
        last_known_path=str(item.absolute_path),
        availability=MediaAvailability.AVAILABLE,
    )


def _bump(outcome: SourceScanOutcome, delta: TrackScanDelta) -> SourceScanOutcome:
    counts = {
        TrackScanDelta.UNCHANGED: outcome.unchanged,
        TrackScanDelta.MODIFIED: outcome.modified,
        TrackScanDelta.ADDED: outcome.added,
        TrackScanDelta.RELINKED: outcome.relinked,
        TrackScanDelta.MISSING: outcome.missing,
    }
    counts[delta] += 1
    return SourceScanOutcome(
        source_id=outcome.source_id,
        availability=outcome.availability,
        unchanged=counts[TrackScanDelta.UNCHANGED],
        modified=counts[TrackScanDelta.MODIFIED],
        added=counts[TrackScanDelta.ADDED],
        relinked=counts[TrackScanDelta.RELINKED],
        missing=counts[TrackScanDelta.MISSING],
        failed=outcome.failed,
        diagnostic=outcome.diagnostic,
    )
