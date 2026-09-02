"""M6.9 REOPENED — LibraryEnrichmentJob (bulk Library enrichment).

Application-layer product operation: an EXPLICIT user action enriches
the whole Library through the canonical provider workflow, with bounded
scheduling (never one Future per library entity), truthful progress,
cache-first incremental behavior, cancellation integrated with the
coordinator's generation/request authority, and safe shutdown.

Design constraints:
- NEVER submits N futures for N entities: a small bounded working set +
  a producer loop that admits the next entity only when a worker frees
  up (backpressure).
- Cache-first: entities that already have persisted knowledge are
  counted as cached and skipped (no network).
- The job NEVER writes canonical metadata, NEVER touches QML, NEVER
  persists its own state: enrichment.db / enrichment-assets remain the
  only authorities.
- Artists are processed before albums (artist identity evidence is
  reused by album resolution); ambiguous/not_found/failed entities are
  counted and the job continues.
- A projection invalidation callback is invoked with coalescing (every
  ``_INVALIDATE_BATCH`` commits) so QML is not flooded per micro-field.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum, auto

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationState,
)
from michi.application.enrichment_service import EnrichmentService

logger = logging.getLogger(__name__)

# Bounded scheduling (M6.9 REOPENED §17): at most this many entities are
# in-flight or admitted at once; the producer admits the next entity only
# when a slot frees up. Never 10.000 Futures.
JOB_MAX_WORKERS = 2
JOB_MAX_PENDING = 8
JOB_INVALIDATE_BATCH = 16


class LibraryEnrichmentJobState(Enum):
    IDLE = auto()
    PREPARING = auto()
    RUNNING = auto()
    CANCELLING = auto()
    CANCELLED = auto()
    COMPLETED = auto()
    PARTIAL = auto()
    FAILED = auto()


@dataclass
class LibraryEnrichmentProgress:  # noqa: N815 (QML projection names)
    """Truthful job progress — counters represent committed/observed
    outcomes, never enqueued futures."""

    state: LibraryEnrichmentJobState = LibraryEnrichmentJobState.IDLE
    totalEntities: int = 0
    processedEntities: int = 0
    totalArtists: int = 0
    processedArtists: int = 0
    totalAlbums: int = 0
    processedAlbums: int = 0
    cachedEntities: int = 0
    matchedEntities: int = 0
    ambiguousEntities: int = 0
    notFoundEntities: int = 0
    failedEntities: int = 0
    currentEntity: str = ""
    progress: float = 0.0
    error: str = ""


class LibraryEnrichmentJob:
    """Bulk enrichment with bounded scheduling and honest progress."""

    def __init__(
        self,
        coordinator: EnrichmentCoordinator,
        service: EnrichmentService,
        albums: Iterable,
        artists: Iterable,
        on_progress: Callable[[LibraryEnrichmentProgress], None] | None = None,
        on_invalidate: Callable[[], None] | None = None,
        *,
        max_workers: int = JOB_MAX_WORKERS,
        max_pending: int = JOB_MAX_PENDING,
        invalidate_batch: int = JOB_INVALIDATE_BATCH,
    ) -> None:
        self._coordinator = coordinator
        self._service = service
        self._albums = list(albums)
        self._artists = list(artists)
        self._on_progress = on_progress
        self._on_invalidate = on_invalidate
        self._max_workers = max_workers
        self._max_pending = max_pending
        self._invalidate_batch = invalidate_batch
        self._progress = LibraryEnrichmentProgress()
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._cancel_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._executor: ThreadPoolExecutor | None = None
        self._pending: list[tuple[str, object]] = []
        self._inflight = 0
        self._commits_since_invalidate = 0
        # Phase-1 artist resolutions (local artist key → external MBID),
        # reused by album evidence — never a second authority.
        self._resolved_artist_external_ids: dict[str, str] = {}

    # -- public API ---------------------------------------------------------

    @property
    def progress(self) -> LibraryEnrichmentProgress:
        with self._lock:
            return LibraryEnrichmentProgress(**self._progress.__dict__)

    def start(self) -> None:
        """Admit the whole library in a controlled pipeline: PREPARING →
        artists first → albums → terminal state."""
        with self._lock:
            if self._progress.state not in (
                LibraryEnrichmentJobState.IDLE,
                LibraryEnrichmentJobState.CANCELLED,
                LibraryEnrichmentJobState.COMPLETED,
                LibraryEnrichmentJobState.PARTIAL,
                LibraryEnrichmentJobState.FAILED,
            ):
                return
            self._progress = LibraryEnrichmentProgress(
                state=LibraryEnrichmentJobState.PREPARING,
                totalArtists=len(self._artists),
                totalAlbums=len(self._albums),
                totalEntities=len(self._artists) + len(self._albums),
            )
            self._cancel_event.clear()
            self._shutdown_event.clear()
        self._publish()
        # PREPARING: filter cache-first entities (persisted knowledge).
        artist_queue = [a for a in self._artists if not self._has_artist_knowledge(a)]
        album_queue = [al for al in self._albums if not self._has_album_knowledge(al)]
        cached = (len(self._artists) + len(self._albums)) - (
            len(artist_queue) + len(album_queue)
        )
        with self._lock:
            self._progress.cachedEntities = cached
            self._progress.state = LibraryEnrichmentJobState.RUNNING
            self._pending = [("artist", a) for a in artist_queue] + [
                ("album", al) for al in album_queue
            ]
            self._inflight = 0
        self._publish()
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="michi-enrich-job",
        )
        try:
            # FASE 1 — artistas (la identidad resuelta se reutiliza como
            # evidencia en los albums; nunca se repite la búsqueda por
            # album — §18).
            with self._lock:
                self._pending = [("artist", a) for a in artist_queue]
            self._drain()
            # FASE 2 — albums (con la evidencia de artista disponible).
            if not self._cancel_event.is_set():
                with self._lock:
                    self._pending = [("album", al) for al in album_queue]
                self._drain()
        finally:
            # Workers finished (or cancelled): close the pool.
            if self._executor is not None:
                self._executor.shutdown(wait=True)
                self._executor = None
        # Empty library (or all entities cache-first): nothing was ever
        # submitted — finalize directly. A cancel mid-drain converges
        # CANCELLING → CANCELLED here.
        with self._lock:
            if self._progress.state in (
                LibraryEnrichmentJobState.RUNNING,
                LibraryEnrichmentJobState.CANCELLING,
            ):
                self._finalize()

    def cancel(self) -> None:
        """Stop admitting new work; the coordinator cancels its in-flight
        operations; the state converges to CANCELLED."""
        with self._lock:
            if self._progress.state not in (
                LibraryEnrichmentJobState.RUNNING,
                LibraryEnrichmentJobState.PREPARING,
            ):
                return
            self._progress.state = LibraryEnrichmentJobState.CANCELLING
            self._cancel_event.set()
        self._coordinator.cancel_all()
        self._publish()

    def shutdown(self) -> None:
        """Container shutdown: cancel + stop admitting; never blocks on
        network — physically-active HTTP calls are left to return."""
        with self._lock:
            self._shutdown_event.set()
            self._cancel_event.set()
            if self._progress.state in (
                LibraryEnrichmentJobState.RUNNING,
                LibraryEnrichmentJobState.PREPARING,
                LibraryEnrichmentJobState.CANCELLING,
            ):
                self._progress.state = LibraryEnrichmentJobState.CANCELLED
        self._coordinator.cancel_all()
        self._publish()

    # -- internals ----------------------------------------------------------

    def _drain(self) -> None:
        """Bounded scheduling with backpressure — the admission loop is
        the SINGLE producer: it admits the next entity only when a slot
        frees up (never one Future per entity) and it waits on the
        condition while the working set is full. Done callbacks only
        notify; they never submit (the pool may be shutting down)."""
        while not self._cancel_event.is_set():
            with self._cond:
                if self._shutdown_event.is_set():
                    break
                if not self._pending and self._inflight == 0:
                    break
                if self._pending and self._inflight < self._max_pending:
                    kind, entity = self._pending.pop(0)
                    self._inflight += 1
                    future = self._executor.submit(self._run_entity, kind, entity)
                    future.add_done_callback(self._entity_done)
                    continue
                # Working set full: wait for a slot (bounded poll).
                self._cond.wait(timeout=0.05)

    def _run_entity(self, kind: str, entity) -> None:
        try:
            if self._cancel_event.is_set():
                return
            if kind == "artist":
                self._enrich_artist(entity)
            else:
                self._enrich_album(entity)
        except Exception as exc:  # noqa: BLE001 — job continues per entity
            logger.warning("enrichment job entity failed: %s", exc)

    def _enrich_artist(self, artist) -> None:
        albums = tuple(
            al
            for al in self._albums
            if getattr(al, "artist_key", "") == getattr(artist, "key", "")
        )
        self._coordinator.enrich_artist(artist, albums, (), on_state=self._on_state)

    def _enrich_album(self, album) -> None:
        # Reuse the artist identity evidence resolved in phase 1 when
        # available (avoids repeating artist searches per album — §18).
        artist_key = getattr(album, "artist_key", "") or ""
        resolved_artist = self._resolved_artist_external_ids.get(artist_key, "")
        self._coordinator.enrich_album(
            album,
            resolved_artist_external_id=resolved_artist,
            on_state=self._on_state,
        )

    def _on_state(self, event) -> None:
        """Coordinator state callback (EnrichmentOperationEvent)."""
        state = event.state
        local_key = event.local_entity_key
        if (
            event.entity_kind.name == "ARTIST"
            and state is EnrichmentOperationState.READY
        ):
            self._remember_resolved_artist(local_key)
        if state in (EnrichmentOperationState.READY, EnrichmentOperationState.PARTIAL):
            self._commit_entity(local_key, "matched")
        elif state is EnrichmentOperationState.AMBIGUOUS:
            self._commit_entity(local_key, "ambiguous")
        elif state is EnrichmentOperationState.NOT_FOUND:
            self._commit_entity(local_key, "not_found")
        elif state is EnrichmentOperationState.FAILED:
            self._commit_entity(local_key, "failed")
        elif state is EnrichmentOperationState.CANCELLED:
            self._commit_entity(local_key, "cancelled")

    def _remember_resolved_artist(self, local_artist_key: str) -> None:
        """Records a phase-1 artist resolution for album evidence reuse."""
        try:
            identity = self._service.get_artist_knowledge(local_artist_key)
            if identity is None:
                return
            # The persisted identity carries the external MBID.
            resolved = getattr(identity, "external_artist_id", "") or ""
            if resolved:
                with self._lock:
                    self._resolved_artist_external_ids[local_artist_key] = resolved
        except Exception:  # noqa: BLE001
            return

    def _commit_entity(self, local_key: str, outcome: str) -> None:
        with self._lock:
            if self._progress.state not in (
                LibraryEnrichmentJobState.RUNNING,
                LibraryEnrichmentJobState.CANCELLING,
            ):
                return
            if self._cancel_event.is_set() and outcome != "cancelled":
                return  # stale commit after cancel: never counted
            self._progress.processedEntities += 1
            self._progress.currentEntity = local_key
            if outcome == "matched":
                self._progress.matchedEntities += 1
            elif outcome == "ambiguous":
                self._progress.ambiguousEntities += 1
            elif outcome == "not_found":
                self._progress.notFoundEntities += 1
            elif outcome == "failed":
                self._progress.failedEntities += 1
            total = max(1, self._progress.totalEntities)
            self._progress.progress = self._progress.processedEntities / total
            self._commits_since_invalidate += 1
            coalesce = self._commits_since_invalidate >= self._invalidate_batch
            if coalesce:
                self._commits_since_invalidate = 0
        if coalesce and self._on_invalidate is not None:
            self._on_invalidate()
        self._publish()

    def _entity_done(self, future) -> None:
        with self._cond:
            self._inflight -= 1
            self._cond.notify_all()

    def _finalize(self) -> None:
        with self._lock:
            if self._progress.state is LibraryEnrichmentJobState.CANCELLING:
                state = LibraryEnrichmentJobState.CANCELLED
            elif (
                self._progress.failedEntities
                and self._progress.failedEntities == self._progress.processedEntities
            ):
                state = LibraryEnrichmentJobState.FAILED
            elif self._progress.failedEntities:
                state = LibraryEnrichmentJobState.PARTIAL
            else:
                state = LibraryEnrichmentJobState.COMPLETED
            self._progress.state = state
            self._progress.currentEntity = ""
            total = max(1, self._progress.totalEntities)
            self._progress.progress = self._progress.processedEntities / total
        if self._on_invalidate is not None:
            self._on_invalidate()
        self._publish()

    def _has_artist_knowledge(self, artist) -> bool:
        key = getattr(artist, "key", "")
        if not key:
            return False
        try:
            return self._service.get_artist_knowledge(key) is not None
        except Exception:  # noqa: BLE001
            return False

    def _has_album_knowledge(self, album) -> bool:
        key = getattr(album, "key", "")
        if not key:
            return False
        try:
            return self._service.get_album_knowledge(key) is not None
        except Exception:  # noqa: BLE001
            return False

    def _publish(self) -> None:
        if self._on_progress is not None:
            self._on_progress(self.progress)
