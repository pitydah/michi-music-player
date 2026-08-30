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
from dataclasses import dataclass, replace
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
from michi.application.ports import MetadataExtractorPort, ScanCancelled
from michi.domain.library import TrackMetadata, TrackRef
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceAvailability,
    SourceLifecycle,
    TrackRecord,
    new_library_source_id,
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
    cache_degraded: bool = False
    diagnostic: str = ""

    @property
    def total(self) -> int:
        return self.unchanged + self.modified + self.added + self.relinked


class SourceOverlapError(ValueError):
    """Adding a source whose root contains (or is contained by) an existing
    source root — typed conflict; never silently index nested roots."""


@dataclass
@dataclass(frozen=True)
class SourceReconciliationPlan:
    """IMMUTABLE worker result (10/10 FINAL SEAL P1-01).

    ``source_snapshot`` is the EXACT immutable LibrarySource configuration
    used to discover/extract/reconcile this plan. Owner-side commit MUST
    compare this snapshot with the current authoritative catalog source
    before any durable or observable write — the plan is self-describing
    evidence, never re-derived from a re-fetched Source."""

    source_snapshot: LibrarySource
    outcome: SourceScanOutcome
    refs: tuple[TrackRef, ...]
    upsert_media: tuple[MediaFileRecord, ...]
    upsert_tracks: tuple[TrackRecord, ...]
    index_upserts: tuple
    cache_upserts: tuple
    new_track_ids: tuple[str, ...]


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
        # P1-04: small in-memory source-record cache (never one SQLite query
        # per TrackId at scale); refreshed on every production mutation.
        self._source_records: dict[str, LibrarySource] = {
            source.library_source_id: source for source in self._catalog.load_sources()
        }

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
        sources = {
            source.library_source_id: source for source in self._catalog.load_sources()
        }
        retired_ids = {
            source_id
            for source_id, source in sources.items()
            if source.lifecycle.value == "retired"
        }
        cache = (
            {Path(path): meta for path, meta in self._index_metadata().items()}
            if self._index is not None
            else {}
        )
        refs: list[TrackRef] = []
        for media in media_by_id.values():
            # P1-04: RETIRED sources stay durable in the catalog but are
            # EXCLUDED from the active hydrated projection (never deleted).
            if media.library_source_id in retired_ids:
                continue
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
        self._library._rebuild_derived_library_state(offline=True)
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

    # -------------------------------------------------------------- sources

    def add_source(self, display_name: str, root_path: str) -> LibrarySource:
        """Add a new ACTIVE source with a typed overlap conflict check
        (M6-EXT-R4 §65): an existing root containing the new root (or vice
        versa) is rejected — /Music and /Music/Classical are never indexed
        as independent roots."""
        root = Path(root_path)
        existing_sources = self._catalog.load_sources()
        for existing in existing_sources:
            existing_root = Path(existing.root_path)
            if root == existing_root:
                if existing.lifecycle is SourceLifecycle.RETIRED:
                    # P1-D: exact same root → reactivate the SAME SourceId.
                    return self.reactivate_source(existing.library_source_id)
                raise SourceOverlapError(f"source root already configured: {root_path}")
            try:
                overlaps = root.is_relative_to(
                    existing_root
                ) or existing_root.is_relative_to(root)
            except ValueError:
                overlaps = False
            if overlaps:
                raise SourceOverlapError(
                    f"source root {root_path} overlaps existing "
                    f"source {existing.root_path}"
                )
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name=display_name.strip() or root.name or "Music",
            root_path=str(root),
        )
        self._catalog.upsert_source(source)
        self._remember_sources(self._catalog.load_sources())
        return source

    # ------------------------------------------------------------ observables

    def list_sources(self) -> tuple[LibrarySource, ...]:
        """Public source management surface (M6-EXT-R4 freeze gate §21):
        presentation consumes THIS, never the repository directly."""
        sources = self._catalog.load_sources()
        self._remember_sources(sources)
        return sources

    def source_counts(self, library) -> dict[str, int]:
        """Track counts per source from the canonical library state."""
        counts: dict[str, int] = {}
        for track in library.state.tracks:
            if track.library_source_id:
                counts[track.library_source_id] = (
                    counts.get(track.library_source_id, 0) + 1
                )
        return counts

    def scan_all_sources(self) -> list[SourceScanOutcome]:
        """Scan ALL ACTIVE + ENABLED sources, serialized (M6-EXT-R4 §13).
        Never parallel; one source at a time."""
        outcomes: list[SourceScanOutcome] = []
        for source in self._catalog.load_sources():
            if source.lifecycle.value == "retired" or not source.enabled:
                continue
            outcomes.append(self.scan_source(source))
        return outcomes

    def relocate_source_root(self, source_id: str, new_root: str) -> LibrarySource:
        """ROOT RELOCATION — ROOT ONLY (CORRECTIVE SEAL §1).

        Validates overlap against OTHER sources, validates existence,
        constructs the relocated LibrarySource preserving LibrarySourceId /
        display name / enabled / lifecycle, persists the new root and
        returns it. It NEVER scans, enumerates, extracts metadata,
        reconciles the catalog or publishes state — the caller decides when
        (and whether) a reconciliation scan runs."""
        root = Path(new_root)
        if not root.exists():
            raise ValueError(f"source root does not exist: {new_root}")
        if not root.is_dir():
            raise ValueError(f"source root is not a directory: {new_root}")
        for other in self._catalog.load_sources():
            if other.library_source_id == source_id:
                continue
            try:
                overlaps = Path(new_root).is_relative_to(Path(other.root_path)) or Path(
                    other.root_path
                ).is_relative_to(Path(new_root))
            except ValueError:
                overlaps = False
            if overlaps:
                raise SourceOverlapError(
                    f"new root {new_root} overlaps existing source {other.root_path}"
                )
        target = None
        for source in self._catalog.load_sources():
            if source.library_source_id == source_id:
                target = source
                break
        if target is None:
            raise ValueError(f"unknown source: {source_id}")
        relocated = LibrarySource(
            library_source_id=target.library_source_id,
            display_name=target.display_name,
            root_path=new_root,
            enabled=target.enabled,
            lifecycle=target.lifecycle,
        )
        self._catalog.upsert_source(relocated)
        self._remember_sources(self._catalog.load_sources())
        # 10/10 FINAL SEAL §9: the old physical observation describes /OLD —
        # /NEW is UNKNOWN until re-probed. Never AVAILABLE optimistically.
        self._observations.pop(source_id, None)
        return relocated

    def relocate_source(self, source_id: str, new_root: str) -> SourceScanOutcome:
        """LEGACY SYNCHRONOUS WRAPPER: relocate_source_root + immediate
        scan. Kept only for non-productive callers; the productive path
        uses ``relocate_source_root`` + the async scan lifecycle."""
        relocated = self.relocate_source_root(source_id, new_root)
        return self.scan_source(relocated)

    def retire_source(self, source_id: str) -> None:
        """Soft retire (Remove from Michi) — never a filesystem delete.
        P1-04: catalog records (MediaFile/Track) and all user references
        survive; the source leaves ONLY the active Library projection."""
        self._catalog.retire_source(source_id)
        self._remember_sources(self._catalog.load_sources())
        self._observations.pop(source_id, None)
        self._library.apply_source_tracks(source_id, [])

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        """Enable/disable a configured source (stays configured)."""
        self._catalog.set_source_enabled(source_id, enabled)
        self._remember_sources(self._catalog.load_sources())
        # P1-04: a re-enabled source is UNKNOWN until actually re-probed —
        # never revive a stale AVAILABLE as current truth.
        self._observations.pop(source_id, None)

    def submit_source_scan(
        self,
        source: LibrarySource,
        pipeline,
        generation: int,
        on_progress=None,
        on_done=None,
    ) -> None:
        """ASYNC source-aware scan (M6-EXT-R4 freeze gate §14): the heavy
        compute runs on the WORKER via the existing M6.4 pipeline; the
        authoritative commit + state publication happen on the OWNER thread
        after the generation gate. A stale/cancelled generation NEVER
        commits — no partial authoritative state, ever.

        ``pipeline`` is a ScanPipelinePort; ``on_done(generation, plan,
        error)`` runs on the owner thread and MUST call
        ``commit_source_reconciliation`` only after validating the
        generation."""

        def work(progress, token, report):
            # P1-05: the WORKER computes facts only — it never mutates
            # ``_observations`` (observable state is owner-published).
            discovered = self._scanner.discover(source)
            progress.phase = "RECONCILING"
            progress.total = len(discovered)
            progress.processed = 0
            for item in discovered:
                if token.cancelled:
                    raise ScanCancelled()
                progress.current_path = str(item.absolute_path)
                progress.processed += 1
                report()
            return self.compute_source_reconciliation(source, discovered, token=token)

        pipeline.submit(generation, work, on_progress, on_done)

    def commit_source_scan_if_current(
        self,
        generation: int,
        current_generation: int,
        plan: "SourceReconciliationPlan | None",
        error: BaseException | None,
    ) -> SourceScanOutcome | None:
        """OWNER-THREAD gate (10/10 FINAL SEAL P1-01): the PLAN carries its
        own provenance. No external Source argument — the worker snapshot is
        the only evidence of what was scanned.

        GATES: 1 generation → 2 worker outcome → 3 catalog configuration →
        4 exact snapshot provenance → 5 ACTIVE+ENABLED. ZERO durable or
        observable writes before Gate 5."""
        if generation != current_generation:
            return None  # stale generations NEVER change observed state
        if error is not None or plan is None:
            return None
        snapshot = plan.source_snapshot
        # Gate 3 — current catalog configuration.
        current = self._current_source_record(snapshot.library_source_id)
        if current is None:
            logger.info(
                "dropping source scan plan: source no longer exists (source_id=%s)",
                snapshot.library_source_id,
            )
            return None
        # Gate 4 — EXACT source configuration provenance (root/enabled/
        # lifecycle) from the plan itself.
        if not self._same_source_configuration(snapshot, current):
            logger.info(
                "dropping stale source scan plan: source configuration "
                "changed during scan "
                "(source_id=%s old_root=%s current_root=%s)",
                snapshot.library_source_id,
                snapshot.root_path,
                current.root_path,
            )
            return None
        # Gate 5 — only ACTIVE + ENABLED is productive.
        if current.lifecycle is not SourceLifecycle.ACTIVE or not current.enabled:
            logger.info(
                "dropping source scan plan for inactive source: %s",
                current.library_source_id,
            )
            return None
        outcome = self.commit_source_reconciliation(current, plan)
        if not outcome.failed:
            self._observations[current.library_source_id] = outcome.availability
        return outcome

    def source_configuration_is_current(self, snapshot: LibrarySource) -> bool:
        """READ-ONLY authority gate (10/10 FINAL SEAL §5): true only when the
        snapshot exactly matches the current catalog configuration AND the
        source is ACTIVE + ENABLED. Never mutates anything."""
        current = self._current_source_record(snapshot.library_source_id)
        if current is None:
            return False
        return (
            self._same_source_configuration(snapshot, current)
            and current.lifecycle is SourceLifecycle.ACTIVE
            and current.enabled
        )

    def _current_source_record(self, source_id: str) -> LibrarySource | None:
        """AUTHORITATIVE commit-boundary lookup (never the stale cache as
        final authority); called once per source commit, not per track."""
        sources = self._catalog.load_sources()
        self._remember_sources(sources)
        return self._source_records.get(source_id)

    @staticmethod
    def _same_source_configuration(
        snapshot: LibrarySource, current: LibrarySource
    ) -> bool:
        return (
            snapshot.library_source_id == current.library_source_id
            and snapshot.root_path == current.root_path
            and snapshot.enabled == current.enabled
            and snapshot.lifecycle == current.lifecycle
        )

    def reactivate_source(self, source_id: str) -> LibrarySource:
        """P1-D: restore a retired/disabled Source preserving its identity.
        No MediaFile/Track deletion, no new SourceId; the physical truth is
        UNKNOWN until the source is re-probed."""
        source = self._current_source_record(source_id)
        if source is None:
            raise ValueError(f"unknown source: {source_id}")
        if source.lifecycle is SourceLifecycle.ACTIVE:
            if source.enabled:
                return source
            restored = replace(source, enabled=True)
        else:
            restored = replace(source, lifecycle=SourceLifecycle.ACTIVE, enabled=True)
        self._catalog.upsert_source(restored)
        self._remember_sources(self._catalog.load_sources())
        self._observations.pop(source_id, None)
        return restored

    def _remember_sources(self, sources: tuple[LibrarySource, ...]) -> None:
        self._source_records = {source.library_source_id: source for source in sources}

    def _source_record(self, source_id: str) -> LibrarySource | None:
        source = self._source_records.get(source_id)
        if source is not None:
            return source
        sources = self._catalog.load_sources()
        self._remember_sources(sources)
        return self._source_records.get(source_id)

    def observed_availability(self, source_id: str) -> SourceAvailability:
        """CONFIGURED-AWARE availability (P1-04): DISABLED/RETIRED
        configuration DOMINATES any physical observation — an old AVAILABLE
        observation never overrides the configured state."""
        source = self._source_record(source_id)
        if source is not None and (
            source.lifecycle.value == "retired" or not source.enabled
        ):
            return SourceAvailability.DISABLED
        return self._observations.get(source_id, SourceAvailability.UNKNOWN)

    # ------------------------------------------------------------------ scan

    def record_source_scan_error(
        self, source_id: str, error: BaseException
    ) -> SourceAvailability:
        """OWNER-THREAD ONLY (P1-05): records the physical observation for a
        worker filesystem failure. ScanCancelled fabricates no observation."""
        if isinstance(error, LibraryFilesystemError):
            availability = _availability_from_code(error.code)
        else:
            availability = SourceAvailability.IO_ERROR
        self._observations[source_id] = availability
        return availability

    def scan_source(self, source: LibrarySource) -> SourceScanOutcome:
        """Reconcile ONE source against its catalog records (synchronous
        convenience path: compute + commit on the caller thread).

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
        plan = self.compute_source_reconciliation(source, discovered)
        return self.commit_source_reconciliation(source, plan)

    # ------------------------------------------------------------------
    # COMPUTE / COMMIT split (M6-EXT-R4 freeze gate §14): the heavy phase
    # (enumeration, fingerprints, metadata extraction, candidate
    # computation) runs on a WORKER; the authoritative catalog commit and
    # state publication run on the OWNER thread after the generation gate.
    # The worker never writes SQLite, caches or state.
    # ------------------------------------------------------------------

    def compute_source_reconciliation(
        self,
        source: LibrarySource,
        discovered: tuple[DiscoveredMediaFile, ...],
        token=None,
    ) -> "SourceReconciliationPlan":
        """PURE-ish compute phase: reads catalog/caches, builds the full
        reconciliation plan. NO durable writes (worker-safe).

        CORRECTIVE SEAL §4: the cancellation token propagates INTO the
        reconciliation — checked before metadata extraction (per item) and
        before the plan is returned, so a cancel during extraction can
        never produce a commit-able plan."""
        return self._reconcile_available(source, discovered, token=token)

    def commit_source_reconciliation(
        self,
        source: LibrarySource,
        plan: "SourceReconciliationPlan",
    ) -> SourceScanOutcome:
        """OWNER-THREAD commit phase (P1-07), THREE separated phases:

        AUTHORITATIVE: the ONE catalog transaction. Failure → failed
        outcome, no state publication, nothing changed.

        REBUILDABLE: index/media caches AFTER the authority committed. A
        cache failure NEVER reverses the authoritative fact — it marks the
        outcome ``cache_degraded`` (rebuildable debt) and publication
        still converges LibraryState to the new authority.

        PUBLICATION: state derived from the reconciliation. A publication
        callback failure is logged and NEVER misreports the authoritative
        transaction (the next scan/hydration converges).

        Callers must pass the generation gate BEFORE calling."""
        outcome = plan.outcome
        # AUTHORITATIVE PHASE
        try:
            self._catalog.apply_source_reconciliation(
                tuple(plan.upsert_media), tuple(plan.upsert_tracks)
            )
        except LibraryCatalogError as exc:
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=SourceAvailability.AVAILABLE,
                failed=True,
                diagnostic=f"catalog commit failed: {exc}",
            )
        # REBUILDABLE PHASE — degradation, never authority reversal.
        degraded = False
        try:
            if self._index is not None and plan.index_upserts:
                self._index.upsert_many(tuple(plan.index_upserts))
        except Exception as exc:  # noqa: BLE001 - rebuildable cache
            degraded = True
            logger.warning("index cache degraded (rebuildable): %s", exc)
        try:
            if self._media_cache is not None and plan.cache_upserts:
                for entry in plan.cache_upserts:
                    self._media_cache.upsert(*entry)
        except Exception as exc:  # noqa: BLE001 - rebuildable cache
            degraded = True
            logger.warning("media cache degraded (rebuildable): %s", exc)
        # PUBLICATION PHASE — the authority already changed; never pretend
        # otherwise on a publication hiccup.
        try:
            self._library.apply_source_tracks(source.library_source_id, plan.refs)
            if plan.new_track_ids:
                self._library.note_new_track_ids(tuple(plan.new_track_ids))
        except Exception as exc:  # noqa: BLE001 - publication is derived
            logger.warning(
                "state publication failed after authoritative commit; "
                "next hydration/scan converges: %s",
                exc,
            )
        return _bump_cache_degraded(outcome, degraded)

    def _reconcile_available(
        self,
        source: LibrarySource,
        discovered: tuple[DiscoveredMediaFile, ...],
        *,
        token=None,
    ) -> "SourceReconciliationPlan":
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

        # PHASE 2 — bounded relink candidates: fresh-MISSING media grouped
        # by cached (device_id, inode) observation. Auto-relink fires ONLY
        # when EXACTLY ONE candidate matches; 0 or >1 candidates (hardlink
        # ambiguity) become a NEW identity and the old media stays MISSING.
        relink_candidates: dict[tuple[int, int], list[MediaFileRecord]] = {}
        for media in missing_updates.values():
            cached = cache.get(media.media_file_id)
            if cached is None or not cached[2] or not cached[3]:
                continue  # no usable relocation evidence
            key = (cached[2], cached[3])
            relink_candidates.setdefault(key, []).append(media)

        # PHASE 3 — discovered items reconcile against known/missing state.
        index_upserts: list[_IndexEntry] = []
        cache_upserts: list[tuple] = []
        for item in discovered:
            if token is not None and token.cancelled:
                raise ScanCancelled()
            known = known_by_path.get(item.relative_path)
            media_id: str
            track: TrackRecord | None
            changed = True  # metadata must re-extract unless proven UNCHANGED

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
                        changed = False  # §15: UNCHANGED reuses cached metadata
                    else:
                        outcome = _bump(outcome, TrackScanDelta.MODIFIED)
            else:
                # CASE B: new relative path → bounded relink candidate.
                key = (item.device_id, item.inode)
                candidates = (
                    relink_candidates.get(key)
                    if item.device_id and item.inode
                    else None
                )
                if candidates is not None and len(candidates) == 1:
                    # EXACT unique same-source move (§16): preserve ids.
                    candidate = candidates[0]
                    media_id = candidate.media_file_id
                    track = track_by_media.get(media_id)
                    upsert_media.append(_media_available(candidate, item))
                    # The relinked media is no longer missing.
                    missing_updates.pop(media_id, None)
                    outcome = _bump(outcome, TrackScanDelta.RELINKED)
                else:
                    # 0 or >1 candidates (hardlink ambiguity): a NEW identity
                    # (authoritative only after the catalog commit); the old
                    # media stays MISSING — never merged.
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

            # §15: MODIFIED/ADDED/RELINKED re-extract metadata (tags changed
            # → fresh facts); UNCHANGED reuses the rebuildable cache with
            # ZERO extraction.
            meta = None if changed else index_meta.get(str(item.absolute_path))
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
            cache_upserts.append(
                (media_id, item.file_size, item.mtime_ns, item.device_id, item.inode)
            )
        if token is not None and token.cancelled:
            raise ScanCancelled()

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

        return SourceReconciliationPlan(
            source_snapshot=source,
            outcome=outcome,
            refs=tuple(refs),
            upsert_media=tuple(upsert_media),
            upsert_tracks=tuple(upsert_tracks),
            index_upserts=tuple(index_upserts),
            cache_upserts=tuple(cache_upserts),
            new_track_ids=tuple(new_track_ids),
        )

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


def _bump_cache_degraded(
    outcome: SourceScanOutcome, degraded: bool
) -> SourceScanOutcome:
    if not degraded or outcome.cache_degraded:
        return outcome
    return SourceScanOutcome(
        source_id=outcome.source_id,
        availability=outcome.availability,
        unchanged=outcome.unchanged,
        modified=outcome.modified,
        added=outcome.added,
        relinked=outcome.relinked,
        missing=outcome.missing,
        failed=outcome.failed,
        cache_degraded=True,
        diagnostic=outcome.diagnostic,
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
