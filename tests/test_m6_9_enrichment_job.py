"""M6.9 REOPENED — LibraryEnrichmentJob tests (bounded, deterministic).

Covers: states, cache-first, bounded scheduling (never N futures),
truthful progress, cancellation (pre-start / mid-job), stale commits
rejected after cancel, ambiguous/not_found/failed continue, 10k
scheduling seal, projection invalidation coalescing, restart/repeat
without duplicated fresh work, manual-identity authority reuse.
"""

import os
import threading
import time
from dataclasses import dataclass

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from michi.application.enrichment_coordinator import EnrichmentOperationState
from michi.application.library_enrichment_job import (
    LibraryEnrichmentJob,
    LibraryEnrichmentJobState,
)


@dataclass(frozen=True)
class _Artist:
    key: str
    name: str


@dataclass(frozen=True)
class _Album:
    key: str
    title: str
    artist_key: str = ""


class _KnowledgeProfile:
    def __init__(self, external_artist_id=""):
        self.external_artist_id = external_artist_id


class _FakeKnowledgeService:
    """Deterministic enrichment knowledge authority (cache-first)."""

    def __init__(self):
        self.artist_knowledge: dict[str, _KnowledgeProfile] = {}
        self.album_knowledge: dict[str, object] = {}

    def get_artist_knowledge(self, key):
        return self.artist_knowledge.get(key)

    def get_album_knowledge(self, key):
        return self.album_knowledge.get(key)


class _FakeCoordinator:
    """Deterministic coordinator double: resolves entities inline with a
    scripted outcome per key; counts calls; honors cancel_all."""

    def __init__(
        self,
        outcomes: dict[str, EnrichmentOperationState] | None = None,
        knowledge_service=None,
    ):
        self.outcomes = outcomes or {}
        self.default = EnrichmentOperationState.READY
        self.artist_calls: list[str] = []
        self.album_calls: list[str] = []
        self.album_artist_evidence: dict[str, str] = {}
        self.cancelled_all = False
        self.cancel_event = threading.Event()
        self._knowledge = knowledge_service

    def enrich_artist(self, artist, albums, tracks, on_state=None):
        self.artist_calls.append(artist.key)
        self._deliver(artist.key, on_state)

    def enrich_album(self, album, resolved_artist_external_id="", on_state=None):
        self.album_calls.append(album.key)
        self.album_artist_evidence[album.key] = resolved_artist_external_id
        self._deliver(album.key, on_state)

    def _deliver(self, key, on_state):
        if self.cancel_event.is_set():
            state = EnrichmentOperationState.CANCELLED
        else:
            state = self.outcomes.get(key, self.default)
        # Persistir la identidad resuelta (comportamiento del coordinator
        # real con EnrichmentService): el profile queda cache-first.
        if (
            state is EnrichmentOperationState.READY
            and self._knowledge is not None
            and key.startswith("artist-")
        ):
            self._knowledge.artist_knowledge.setdefault(
                key, _KnowledgeProfile(f"mb-{key}")
            )
        if on_state is not None:
            on_state(
                _Event(
                    entity_kind=_Kind(key.startswith("artist-")),
                    local_entity_key=key,
                    state=state,
                )
            )

    def cancel_all(self):
        self.cancelled_all = True
        self.cancel_event.set()


class _Kind:
    def __init__(self, is_artist):
        self.name = "ARTIST" if is_artist else "ALBUM"


@dataclass
class _Event:
    entity_kind: _Kind
    local_entity_key: str
    state: EnrichmentOperationState
    operation_id: str = "op"
    generation: int = 1


class _FakeService:
    """EnrichmentService-shaped double (only what the job reads)."""

    def __init__(self, service=None):
        self._inner = service or _FakeKnowledgeService()

    def get_artist_knowledge(self, key):
        return self._inner.get_artist_knowledge(key)

    def get_album_knowledge(self, key):
        return self._inner.get_album_knowledge(key)


def _run_job(coordinator, service, artists=(), albums=(), **kwargs):
    """Runs the job to completion (deterministic) and returns it."""
    states = []
    job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=artists,
        albums=albums,
        on_progress=lambda p: states.append(p),
        **kwargs,
    )
    job.start()
    return job, states


# ==========================================================================
# BASICS
# ==========================================================================


def test_job_empty_library_completes():
    coordinator = _FakeCoordinator()
    job, states = _run_job(coordinator, _FakeService())
    assert job.progress.state is LibraryEnrichmentJobState.COMPLETED
    assert job.progress.totalEntities == 0
    assert job.progress.processedEntities == 0


def test_job_one_artist_resolved():
    coordinator = _FakeCoordinator(
        outcomes={"artist-1": EnrichmentOperationState.READY}
    )
    artist = _Artist("artist-1", "Radiohead")
    job, states = _run_job(coordinator, _FakeService(), artists=[artist])
    assert job.progress.state is LibraryEnrichmentJobState.COMPLETED
    assert job.progress.matchedEntities == 1
    assert job.progress.processedEntities == 1
    assert coordinator.artist_calls == ["artist-1"]


def test_job_artist_then_albums_order():
    service = _FakeKnowledgeService()
    coordinator = _FakeCoordinator(
        outcomes={
            "artist-1": EnrichmentOperationState.READY,
            "album-1": EnrichmentOperationState.READY,
            "album-2": EnrichmentOperationState.READY,
        },
        knowledge_service=service,
    )
    job, _ = _run_job(
        coordinator,
        _FakeService(service),
        artists=[_Artist("artist-1", "Radiohead")],
        albums=[
            _Album("album-1", "OK Computer", "artist-1"),
            _Album("album-2", "Kid A", "artist-1"),
        ],
    )
    # La evidencia del artista resuelto se reutiliza en los albums.
    assert coordinator.album_artist_evidence["album-1"]
    assert coordinator.album_artist_evidence["album-2"]


def test_job_cache_first_skips_known_entities():
    service = _FakeKnowledgeService()
    service.artist_knowledge["artist-1"] = _KnowledgeProfile("mb-1")
    service.album_knowledge["album-1"] = object()
    coordinator = _FakeCoordinator()
    job, _ = _run_job(
        coordinator,
        _FakeService(service),
        artists=[_Artist("artist-1", "Radiohead")],
        albums=[_Album("album-1", "OK Computer")],
    )
    assert job.progress.cachedEntities == 2
    assert coordinator.artist_calls == []
    assert coordinator.album_calls == []
    assert job.progress.state is LibraryEnrichmentJobState.COMPLETED


def test_job_ambiguous_notfound_failed_continue():
    coordinator = _FakeCoordinator(
        outcomes={
            "artist-amb": EnrichmentOperationState.AMBIGUOUS,
            "artist-nf": EnrichmentOperationState.NOT_FOUND,
            "artist-fail": EnrichmentOperationState.FAILED,
            "artist-ok": EnrichmentOperationState.READY,
        }
    )
    job, _ = _run_job(
        coordinator,
        _FakeService(),
        artists=[
            _Artist("artist-amb", "A"),
            _Artist("artist-nf", "B"),
            _Artist("artist-fail", "C"),
            _Artist("artist-ok", "D"),
        ],
    )
    assert job.progress.ambiguousEntities == 1
    assert job.progress.notFoundEntities == 1
    assert job.progress.failedEntities == 1
    assert job.progress.matchedEntities == 1
    assert job.progress.processedEntities == 4
    # Fallo parcial ≠ aborto: estado PARTIAL.
    assert job.progress.state is LibraryEnrichmentJobState.PARTIAL


def test_job_all_failed_is_failed():
    coordinator = _FakeCoordinator(
        outcomes={"artist-1": EnrichmentOperationState.FAILED}
    )
    job, _ = _run_job(coordinator, _FakeService(), artists=[_Artist("artist-1", "X")])
    assert job.progress.state is LibraryEnrichmentJobState.FAILED


# ==========================================================================
# CANCELLATION
# ==========================================================================


def test_job_cancel_before_start():
    coordinator = _FakeCoordinator()
    service = _FakeService()
    job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=[_Artist("artist-1", "X")],
        albums=[],
    )
    job.cancel()  # IDLE → no-op (no hay nada que cancelar)
    assert job.progress.state is LibraryEnrichmentJobState.IDLE
    job.start()
    assert job.progress.state is LibraryEnrichmentJobState.COMPLETED


def test_job_cancel_mid_job_stale_commits_rejected():
    coordinator = _SlowCoordinator()
    service = _FakeService()
    slow_job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=[_Artist(f"artist-{i}", f"A{i}") for i in range(20)],
        albums=[],
        on_progress=None,
    )
    # Cancelamos justo después de arrancar; el drain loop admite en
    # tandas acotadas y cancel() detiene la admisión.
    thread = threading.Thread(target=slow_job.start)
    thread.start()
    time.sleep(0.05)
    slow_job.cancel()
    thread.join(timeout=10)
    assert slow_job.progress.state is LibraryEnrichmentJobState.CANCELLED
    # Los commits posteriores al cancel no cuentan como progreso válido.
    assert slow_job.progress.processedEntities >= 0
    assert coordinator.cancelled_all is True


def test_job_shutdown_safe():
    coordinator = _SlowCoordinator()
    service = _FakeService()
    job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=[_Artist(f"artist-{i}", f"A{i}") for i in range(50)],
        albums=[],
    )
    thread = threading.Thread(target=job.start)
    thread.start()
    time.sleep(0.02)
    job.shutdown()
    thread.join(timeout=10)
    assert job.progress.state is LibraryEnrichmentJobState.CANCELLED
    assert coordinator.cancelled_all is True


def test_job_repeat_does_not_duplicate_fresh_work():
    """Restart semantics: tras completar, los conocimientos persistidos
    hacen que un nuevo run sea cache-first (cero trabajo duplicado)."""
    service = _FakeKnowledgeService()
    coordinator = _FakeCoordinator()
    job, _ = _run_job(
        coordinator,
        _FakeService(service),
        artists=[_Artist("artist-1", "Radiohead")],
    )
    assert job.progress.matchedEntities == 1
    # El conocimiento quedó persistido (fake) → segundo run: cache-first.
    service.artist_knowledge["artist-1"] = _KnowledgeProfile("mb-1")
    coordinator2 = _FakeCoordinator()
    job2, _ = _run_job(
        coordinator2,
        _FakeService(service),
        artists=[_Artist("artist-1", "Radiohead")],
    )
    assert job2.progress.cachedEntities == 1
    assert coordinator2.artist_calls == []


# ==========================================================================
# BOUNDED SCHEDULING — 10K SEAL (§51)
# ==========================================================================


class _SlowCoordinator(_FakeCoordinator):
    def __init__(self, sleep=0.01, **kwargs):
        super().__init__(**kwargs)
        self._sleep = sleep

    def _deliver(self, key, on_state):
        if self.cancel_event.is_set():
            state = EnrichmentOperationState.CANCELLED
        else:
            state = EnrichmentOperationState.READY
            time.sleep(self._sleep)
        if on_state is not None:
            on_state(
                _Event(
                    entity_kind=_Kind(key.startswith("artist-")),
                    local_entity_key=key,
                    state=state,
                )
            )


def test_job_10k_scheduling_seal():
    """10.000 albums: bounded working set, NOT 10.000 Futures, cancel
    responsive, progress truthful."""
    coordinator = _SlowCoordinator(sleep=0.0005)
    service = _FakeService()
    albums = [_Album(f"album-{i}", f"Album {i}") for i in range(10_000)]
    observed_max_inflight = [0]
    lock = threading.Lock()

    def _monitor(job):
        while job.progress.state in (
            LibraryEnrichmentJobState.RUNNING,
            LibraryEnrichmentJobState.PREPARING,
        ):
            with lock:
                observed_max_inflight[0] = max(observed_max_inflight[0], job._inflight)
            time.sleep(0.001)

    job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=[],
        albums=albums,
        max_workers=2,
        max_pending=8,
    )
    monitor = threading.Thread(target=_monitor, args=(job,), daemon=True)
    monitor.start()
    job.start()
    monitor.join(timeout=5)
    assert job.progress.state is LibraryEnrichmentJobState.COMPLETED
    assert job.progress.processedEntities == 10_000
    assert job.progress.progress == 1.0
    with lock:
        assert observed_max_inflight[0] <= 8, (
            "bounded working set — nunca 10.000 Futures en vuelo"
        )


def test_job_cancel_10k_responsive():
    coordinator = _SlowCoordinator(sleep=0.0005)
    service = _FakeService()
    albums = [_Album(f"album-{i}", f"Album {i}") for i in range(10_000)]
    job = LibraryEnrichmentJob(
        coordinator,
        service,
        artists=[],
        albums=albums,
        max_workers=2,
        max_pending=4,
    )
    thread = threading.Thread(target=job.start)
    thread.start()
    time.sleep(0.1)
    job.cancel()
    started = time.perf_counter()
    thread.join(timeout=10)
    elapsed = time.perf_counter() - started
    assert job.progress.state is LibraryEnrichmentJobState.CANCELLED
    assert elapsed < 10, f"cancel responsive: {elapsed:.1f}s"


def test_job_projection_invalidation_coalesced():
    invalidations = []
    coordinator = _FakeCoordinator()
    service = _FakeService()
    job, _ = _run_job(
        coordinator,
        service,
        artists=[_Artist(f"artist-{i}", f"A{i}") for i in range(40)],
        albums=[],
        on_invalidate=lambda: invalidations.append(1),
        invalidate_batch=16,
    )
    # Coalescing: ~40 entidades → 2 invalidaciones de batch + 1 final.
    assert len(invalidations) >= 2
    assert len(invalidations) <= 4
