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
import os
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
from michi.application.ports import (
    MetadataExtractionError,
    MetadataExtractorPort,
    ScanCancelled,
)
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


class _SameRootRetiredError(Exception):
    """Internal signal: the exact root belongs to a RETIRED Source — the
    caller must reactivate the SAME SourceId instead of creating a new one."""

    def __init__(self, source_id: str) -> None:
        super().__init__(source_id)
        self.source_id = source_id


class SourceOverlapError(ValueError):
    """Adding a source whose root contains (or is contained by) an existing
    source root — typed conflict; never silently index nested roots."""


@dataclass(frozen=True)
class SourceReconciliationPlan:
    """IMMUTABLE worker result (10/10 FINAL SEAL P1-01).

    ``source_snapshot`` is the EXACT immutable LibrarySource configuration
    used to discover/extract/reconcile this plan. ``source_config_epoch``
    is the process-local monotonic configuration generation captured at
    submission — the ABA seal. Owner-side commit MUST compare BOTH the
    snapshot fields AND the epoch against the current authoritative catalog
    source before any durable or observable write — the plan is
    self-describing evidence, never re-derived from a re-fetched Source."""

    source_snapshot: LibrarySource
    source_config_epoch: int
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
        artwork_refresh=None,
    ) -> None:
        self._library = library
        self._catalog = catalog
        self._scanner = scanner
        self._media_cache = media_cache
        self._metadata_extractor = metadata_extractor
        self._index = index
        # P1/PERF-LIB-12: async artwork refresh (owner-gated, worker-probed).
        self._artwork_refresh = artwork_refresh
        self._observations: dict[str, SourceAvailability] = {}
        # P1-04: small in-memory source-record cache (never one SQLite query
        # per TrackId at scale); refreshed on every production mutation.
        initial_sources = self._catalog.load_sources()
        self._source_records: dict[str, LibrarySource] = {
            source.library_source_id: source for source in initial_sources
        }
        # TRUE FINAL FREEZE P1-01: process-local monotonic configuration
        # generation per source — the ABA seal. Persisted nowhere: no scan
        # worker survives process shutdown, so durability adds no
        # correctness, only schema/authority blast radius.
        self._source_config_epochs: dict[str, int] = {
            source.library_source_id: 0 for source in initial_sources
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
        # P1-05 R4: hydration renderiza desde cache SIN provider I/O — el
        # arranque offline nunca toca media inalcanzable.
        self._library._rebuild_derived_library_state(offline=True, cache_only=True)
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

    @staticmethod
    def _normalize_source_root(
        raw: str,
        *,
        require_existing: bool,
    ) -> Path:
        """P1-LIB-10 ONE root canonicalization for NEW add/relocate
        mutations: expand user syntax, require absolute, normalize
        lexically. Never mutates legacy persisted records."""
        root = Path(raw).expanduser()
        if not root.is_absolute():
            raise ValueError("music source root must be absolute")
        root = Path(os.path.normpath(str(root)))
        if require_existing:
            if not root.exists():
                raise ValueError(f"music source root does not exist: {root}")
            if not root.is_dir():
                raise ValueError(f"music source root is not a directory: {root}")
        return root

    @staticmethod
    def _physical_evidence(root: Path) -> Path | None:
        """Resolved physical path used ONLY as overlap evidence; falls back
        to lexical when resolution is unavailable — never fabricated."""
        try:
            return root.resolve(strict=False)
        except (OSError, RuntimeError):
            return None

    @classmethod
    def _roots_overlap(cls, a: Path, b: Path) -> bool:
        """Lexical overlap OR resolvable physical overlap (P1-LIB-10): a
        symlink alias of an existing configured root is a typed conflict."""
        try:
            if a.is_relative_to(b) or b.is_relative_to(a):
                return True
        except ValueError:
            pass
        physical_a = cls._physical_evidence(a)
        physical_b = cls._physical_evidence(b)
        if physical_a is not None and physical_b is not None:
            try:
                if physical_a.is_relative_to(physical_b) or physical_b.is_relative_to(
                    physical_a
                ):
                    return True
            except ValueError:
                pass
        return False

    def _schedule_artwork_convergence(self) -> None:
        """NEGATIVE-EVIDENCE SEAL: rebuild artwork work from CURRENT source
        truth.

        Source configuration/availability changes invalidate old physical
        assumptions, but healthy Sources must continue converging. schedule()
        → generation++ → snapshot CURRENT albums → source-aware eligibility
        → unhealthy Source excluded → healthy Sources retained → active
        stale worker cancelled → latest pending snapshot replaces old
        pending. NEVER hard-invalidate (invalidate() would drop the latest
        pending healthy work and starve refresh).

        ABSOLUTE FINAL CLOSURE — DERIVED AUTHORITY FIREWALL: artwork is
        derived, rebuildable, non-authoritative. A throwing schedule() must
        NEVER fail/reclassify/rollback an already committed Source/Catalog
        result: the broad catch is correct HERE precisely because this
        helper is the derived-state firewall — SourceAvailability, TrackId,
        MediaFileId, the Catalog transaction and LibrarySourceId were all
        already determined by the caller. NO rethrow."""
        refresh = self._artwork_refresh
        if refresh is None:
            return
        schedule = getattr(refresh, "schedule", None)
        if schedule is None:
            return
        try:
            schedule()
        except Exception:
            logger.exception(
                "Artwork convergence scheduling failed; "
                "Library source/catalog authority remains committed"
            )

    def _ensure_no_overlap(self, root: Path, existing_sources) -> None:
        for existing in existing_sources:
            existing_root = Path(existing.root_path)
            if root == existing_root:
                if existing.lifecycle is SourceLifecycle.RETIRED:
                    # P1-D: exact same root → reactivate the SAME SourceId.
                    raise _SameRootRetiredError(existing.library_source_id)
                raise SourceOverlapError(f"source root already configured: {root}")
            if self._roots_overlap(root, existing_root):
                raise SourceOverlapError(
                    f"source root {root} overlaps existing source {existing.root_path}"
                )

    def add_source(self, display_name: str, root_path: str) -> LibrarySource:
        """Add a new ACTIVE source with a typed overlap conflict check
        (M6-EXT-R4 §65 + P1-LIB-10): relative roots are rejected and
        lexical OR physical (alias) overlap is a typed conflict."""
        root = self._normalize_source_root(root_path, require_existing=True)
        existing_sources = self._catalog.load_sources()
        try:
            self._ensure_no_overlap(root, existing_sources)
        except _SameRootRetiredError as retired:
            # P1-D: exact same root → reactivate the SAME SourceId.
            return self.reactivate_source(retired.source_id)
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
        root = self._normalize_source_root(new_root, require_existing=True)
        for other in self._catalog.load_sources():
            if other.library_source_id == source_id:
                continue
            if self._roots_overlap(root, Path(other.root_path)):
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
            root_path=str(root),
            enabled=target.enabled,
            lifecycle=target.lifecycle,
        )
        self._catalog.upsert_source(relocated)
        self._remember_sources(self._catalog.load_sources())
        # 10/10 FINAL SEAL §9: the old physical observation describes /OLD —
        # /NEW is UNKNOWN until re-probed. Never AVAILABLE optimistically.
        self._observations.pop(source_id, None)
        # NEGATIVE-EVIDENCE SEAL: el worker en vuelo aún contiene rutas OLD
        # → reschedulea el mundo artwork actual (OLD excluido por UNKNOWN,
        # fuentes sanas NO afectadas). Nunca invalidate() sin reemplazo.
        self._schedule_artwork_convergence()
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
        # P1-05 R4: la publicación estructural al retirar es cache-only
        # (sin probing de Mutagen/directorios en el owner).
        self._library.apply_source_tracks(source_id, [], cache_only=True)
        # ABSOLUTE FINAL SEAL: retirar cambia la composición de albums —
        # el artwork refresh invalida el trabajo en vuelo (nunca se lanza
        # un worker para probar media de la fuente retirada: con cero
        # albums no arranca ningún worker nuevo). Firewalled: un fallo de
        # artwork NUNCA revierte el retire (DERIVED AUTHORITY FIREWALL).
        self._schedule_artwork_convergence()

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        """Enable/disable a configured source (stays configured)."""
        self._catalog.set_source_enabled(source_id, enabled)
        self._remember_sources(self._catalog.load_sources())
        # P1-04: a re-enabled source is UNKNOWN until actually re-probed —
        # never revive a stale AVAILABLE as current truth.
        self._observations.pop(source_id, None)
        # NEGATIVE-EVIDENCE SEAL: converger al subset sano (el source
        # disable/enable se excluye por UNKNOWN/DISABLED; los demás siguen).
        self._schedule_artwork_convergence()

    def submit_source_scan(
        self,
        source: LibrarySource,
        pipeline,
        generation: int,
        on_progress=None,
        on_done=None,
        source_config_epoch: int | None = None,
    ) -> None:
        """ASYNC source-aware scan (M6-EXT-R4 freeze gate §14): the heavy
        compute runs on the WORKER via the existing M6.4 pipeline; the
        authoritative commit + state publication happen on the OWNER thread
        after the generation gate. A stale/cancelled generation NEVER
        commits — no partial authoritative state, ever.

        ``pipeline`` is a ScanPipelinePort; ``on_done(generation, plan,
        error)`` runs on the owner thread and MUST call
        ``commit_source_reconciliation`` only after validating the
        generation.

        TRUE FINAL FREEZE P1-01: the source config epoch is captured HERE
        (owner/application call) BEFORE any worker discovery — the worker
        closure uses the captured value and NEVER reads the coordinator
        epoch map from the worker thread."""

        if source_config_epoch is None:
            source_config_epoch = self.source_config_epoch(source.library_source_id)
        captured_epoch = source_config_epoch
        # Frozen legacy mocks replace compute_source_reconciliation with a
        # pre-epoch signature — detect support ONCE and degrade gracefully
        # (the real production method always supports the new kwargs).
        compute_kwargs = self._compute_supported_kwargs()

        def work(progress, token, report):
            # P1-05: the WORKER computes facts only — it never mutates
            # ``_observations`` (observable state is owner-published).
            # TRUE FINAL FREEZE P2: progress phases are TRUTHFUL —
            # ``processed`` counts reconciled items, not enumerated ones.
            progress.phase = "DISCOVERING"
            progress.current_path = None
            progress.processed = 0
            progress.total = 0
            report()
            # CONCURRENCY-LIB-03A: the productive walk is cooperatively
            # cancellable (legacy fakes inherit the plain-discover default).
            discover = getattr(self._scanner, "discover_cancellable", None)
            if discover is not None:
                discovered = discover(source, token=token)
            else:
                discovered = self._scanner.discover(source)
            progress.phase = "RECONCILING"
            progress.total = len(discovered)
            progress.processed = 0
            progress.current_path = None
            report()

            def on_item_started(item):
                progress.current_path = str(item.absolute_path)
                report()

            def on_item_completed(item):
                progress.processed += 1
                report()

            def on_phase_change(phase, total):
                progress.phase = phase
                progress.processed = 0
                progress.total = total
                report()

            kwargs = {}
            if "source_config_epoch" in compute_kwargs:
                kwargs["source_config_epoch"] = captured_epoch
            if "on_item_started" in compute_kwargs:
                kwargs["on_item_started"] = on_item_started
            if "on_item_completed" in compute_kwargs:
                kwargs["on_item_completed"] = on_item_completed
            if "on_phase_change" in compute_kwargs:
                kwargs["on_phase_change"] = on_phase_change
            return self.compute_source_reconciliation(
                source, discovered, token=token, **kwargs
            )

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
        # Gate 4 — TRUE FINAL FREEZE P1-01 ABA seal: the plan carries the
        # process-local configuration epoch captured at submission. Value
        # equality cannot prove "no intermediate mutation" — the epoch can.
        current_epoch = self._source_config_epochs.get(snapshot.library_source_id, 0)
        if plan.source_config_epoch != current_epoch:
            logger.info(
                "dropping stale source scan plan: configuration epoch "
                "changed (source_id=%s plan_epoch=%s current_epoch=%s)",
                snapshot.library_source_id,
                plan.source_config_epoch,
                current_epoch,
            )
            return None
        # Gate 4b — EXACT source configuration provenance (root/enabled/
        # lifecycle) from the plan itself. Defense in depth: BOTH the epoch
        # AND the fields must match.
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
            # P1-E: la verdad física del source se publica ANTES de que el
            # artwork decida si ese source puede tocarse.
            self._observations[current.library_source_id] = outcome.availability
            # MERGE-READINESS P1: NUNCA schedule() directo — el firewall de
            # autoridad derivada. Un fallo de artwork aquí NO puede escapar:
            # SourceScanLifecycle._finish() debe ejecutarse siempre, o el
            # lifecycle quedaría stall (_active forever, Scan All muerto)
            # aunque el commit de Source ya fue exitoso.
            self._schedule_artwork_convergence()
        return outcome

    def source_configuration_is_current(
        self,
        snapshot: LibrarySource,
        source_config_epoch: int,
    ) -> bool:
        """READ-ONLY authority gate (10/10 FINAL SEAL §5): true only when
        the snapshot exactly matches the current catalog configuration AND
        the epoch matches the current generation AND the source is
        ACTIVE + ENABLED. Never mutates anything."""
        current = self._current_source_record(snapshot.library_source_id)
        if current is None:
            return False
        current_epoch = self._source_config_epochs.get(snapshot.library_source_id, 0)
        return (
            source_config_epoch == current_epoch
            and self._same_source_configuration(snapshot, current)
            and current.lifecycle is SourceLifecycle.ACTIVE
            and current.enabled
        )

    def _compute_supported_kwargs(self) -> frozenset[str]:
        """Compatibility seam: frozen legacy mocks wrap compute with older
        signatures; production always supports the full set. Each optional
        kwarg is feature-detected individually."""
        try:
            import inspect

            return frozenset(
                inspect.signature(self.compute_source_reconciliation).parameters
            )
        except (TypeError, ValueError):
            return frozenset()

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
        # NEGATIVE-EVIDENCE SEAL: el source restaurado es UNKNOWN hasta su
        # scan real — no se proba aún, pero las fuentes sanas no se
        # privan de refresco.
        self._schedule_artwork_convergence()
        return restored

    @staticmethod
    def _scan_config_signature(source: LibrarySource) -> tuple:
        """SCAN-AFFECTING configuration only: root / enabled / lifecycle.
        display_name is presentation metadata — never scan-affecting."""
        return (
            source.root_path,
            source.enabled,
            source.lifecycle,
        )

    def _remember_sources(self, sources: tuple[LibrarySource, ...]) -> None:
        """ONE mutation-detection chokepoint: every production mutation
        already refreshes the source cache after its catalog write, so the
        epoch bumps here — never duplicated in each mutation method."""
        next_records = {source.library_source_id: source for source in sources}
        previous_records = self._source_records
        for source_id, current in next_records.items():
            previous = previous_records.get(source_id)
            if source_id not in self._source_config_epochs:
                self._source_config_epochs[source_id] = 0
            elif previous is not None and self._scan_config_signature(
                previous
            ) != self._scan_config_signature(current):
                self._source_config_epochs[source_id] += 1
        self._source_records = next_records
        # Hard deletion is not the normal R4 lifecycle, but do not retain
        # runtime tokens for genuinely vanished Sources.
        for source_id in tuple(self._source_config_epochs):
            if source_id not in next_records:
                self._source_config_epochs.pop(source_id, None)

    def source_config_epoch(self, source_id: str) -> int:
        """PUBLIC APPLICATION READ of the process-local config generation.
        Synchronizes the source cache against the authoritative catalog
        BEFORE exposing the token (never a stale cache as truth)."""
        self._current_source_record(source_id)
        return self._source_config_epochs.get(source_id, 0)

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
        # NEGATIVE-EVIDENCE SEAL: la verdad del source se publica PRIMERO;
        # el artwork converge al mundo actual (el source fallido queda
        # excluido del snapshot automáticamente; los sanos siguen).
        self._schedule_artwork_convergence()
        return availability

    def scan_source(self, source: LibrarySource) -> SourceScanOutcome:
        """Reconcile ONE source against its catalog records (synchronous
        convenience path: compute + commit on the caller thread).

        NEGATIVE-EVIDENCE SEAL §22: semantically IDENTICAL to the async
        owner path —

            error path:  observation FIRST (typed) → ONE artwork schedule
            success:     authoritative commit → observation AFTER commit →
                         ONE artwork schedule
            commit fail: NO artwork schedule based on failed reconciliation

        RETIRED/disabled sources are skipped entirely (no writes)."""
        if source.lifecycle.value == "retired" or not source.enabled:
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=SourceAvailability.DISABLED,
            )

        try:
            discovered = self._scanner.discover(source)
        except LibraryFilesystemError as exc:
            availability = self.record_source_scan_error(source.library_source_id, exc)
            return SourceScanOutcome(
                source_id=source.library_source_id,
                availability=availability,
                diagnostic=exc.detail or exc.code.value,
            )

        plan = self.compute_source_reconciliation(source, discovered)
        outcome = self.commit_source_reconciliation(source, plan)
        if not outcome.failed:
            # §26/§23: la observación se publica DESPUÉS del commit
            # autoritativo y ANTES del schedule de artwork.
            self._observations[source.library_source_id] = outcome.availability
            self._schedule_artwork_convergence()
        return outcome

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
        *,
        source_config_epoch: int | None = None,
        on_item_started=None,
        on_item_completed=None,
        on_phase_change=None,
    ) -> "SourceReconciliationPlan":
        """PURE-ish compute phase: reads catalog/caches, builds the full
        reconciliation plan. NO durable writes (worker-safe).

        CORRECTIVE SEAL §4: the cancellation token propagates INTO the
        reconciliation — checked before metadata extraction (per item) and
        before the plan is returned, so a cancel during extraction can
        never produce a commit-able plan.

        TRUE FINAL FREEZE P1-01: ``source_config_epoch`` is None only for
        synchronous/test callers — the CURRENT value is resolved before
        reconciliation. The plan carries the epoch so the owner commit can
        apply the ABA seal."""
        if source_config_epoch is None:
            source_config_epoch = self.source_config_epoch(source.library_source_id)
        return self._reconcile_available(
            source,
            discovered,
            token=token,
            source_config_epoch=source_config_epoch,
            on_item_started=on_item_started,
            on_item_completed=on_item_completed,
            on_phase_change=on_phase_change,
        )

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
        # otherwise on a publication hiccup. P1/PERF-LIB-12: structural
        # publication is CACHE-ONLY (no ArtworkProvider I/O on the owner
        # thread); the async artwork refresh re-probes the provider.
        try:
            self._library.apply_source_tracks(
                source.library_source_id, plan.refs, cache_only=True
            )
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
        source_config_epoch: int,
        on_item_started=None,
        on_item_completed=None,
        on_phase_change=None,
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

        # PHASE 2 — STRONG relink evidence (P1-LIB-09): (device_id,
        # inode, file_size, mtime_ns). Only non-zero usable physical IDs
        # participate. A normal rename/move preserves all four facts;
        # inode reuse changes size/mtime and is therefore rejected.
        missing_candidates_by_evidence: dict[tuple, list[MediaFileRecord]] = {}
        for media in missing_updates.values():
            cached = cache.get(media.media_file_id)
            if cached is None or not cached[2] or not cached[3]:
                continue  # no usable relocation evidence
            evidence = (cached[2], cached[3], cached[0], cached[1])
            missing_candidates_by_evidence.setdefault(evidence, []).append(media)

        # PHASE 3 — discovered items reconcile against known/missing state.
        index_upserts: list[_IndexEntry] = []
        cache_upserts: list[tuple] = []
        # P1-LIB-09: pre-group ALL discovered paths by physical evidence so
        # the 1↔1 guard sees the FULL destination set (a second hardlink
        # discovered later must invalidate the first one's relink too).
        discovered_by_evidence: dict[tuple, list] = {}
        for item in discovered:
            if item.device_id and item.inode:
                discovered_by_evidence.setdefault(
                    (item.device_id, item.inode, item.file_size, item.mtime_ns),
                    [],
                ).append(item)
        for item in discovered:
            if token is not None and token.cancelled:
                raise ScanCancelled()
            if on_item_started is not None:
                on_item_started(item)
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
                # CASE B: new relative path → STRONG 1↔1 relink evidence.
                # Legal ONLY when exactly ONE missing candidate AND exactly
                # ONE discovered path share the same evidence tuple —
                # otherwise (inode reuse, hardlink destination ambiguity)
                # a NEW identity is allocated and the old media stays
                # MISSING. Conservative false-negative > false-positive
                # identity merge.
                evidence = (
                    item.device_id,
                    item.inode,
                    item.file_size,
                    item.mtime_ns,
                )
                candidates = (
                    missing_candidates_by_evidence.get(evidence)
                    if item.device_id and item.inode
                    else None
                )
                discovered_count = len(discovered_by_evidence.get(evidence, ()))
                if (
                    candidates is not None
                    and len(candidates) == 1
                    and discovered_count == 1
                ):
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
            if on_item_completed is not None:
                on_item_completed(item)
        if token is not None and token.cancelled:
            raise ScanCancelled()

        # PHASE 4 — persist the fresh MISSING records and project them.
        # CONCURRENCY-LIB-03B: truthful MARKING_MISSING phase with
        # per-item cancellation and progress.
        if on_phase_change is not None:
            on_phase_change("MARKING_MISSING", len(missing_updates))
        for media in missing_updates.values():
            if token is not None and token.cancelled:
                raise ScanCancelled()
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
            if on_item_completed is not None:
                on_item_completed(media)

        return SourceReconciliationPlan(
            source_snapshot=source,
            source_config_epoch=source_config_epoch,
            outcome=outcome,
            refs=tuple(refs),
            upsert_media=tuple(upsert_media),
            upsert_tracks=tuple(upsert_tracks),
            index_upserts=tuple(index_upserts),
            cache_upserts=tuple(cache_upserts),
            new_track_ids=tuple(new_track_ids),
        )

    def _extract_meta(self, path: Path) -> TrackMetadata:
        """P1-LIB-08 FAIL-CLOSED metadata: a typed filesystem failure
        (MetadataExtractionError) is NEVER converted into a fabricated
        success that could be cached under the new fingerprint. The
        infrastructure extractor already owns the "readable but untagged"
        fallback; the coordinator preserves the distinction."""
        if self._metadata_extractor is None:
            return TrackMetadata(title=path.stem)
        try:
            return self._metadata_extractor.extract(path)
        except MetadataExtractionError:
            raise
        except Exception:
            logger.exception("metadata extractor contract violation for %s", path)
            raise

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


@dataclass(frozen=True)
class _IndexEntry:
    """Path-keyed rebuildable metadata cache entry (index repo shape).

    TRUE FINAL FREEZE P2: the plan claims immutability — every meaningful
    carrier must actually be immutable."""

    track_id: str
    file_size: int
    mtime_ns: int
    metadata: TrackMetadata


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
