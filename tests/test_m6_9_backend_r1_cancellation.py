"""M6.9-BACKEND-R1 — per-operation cancellation + async search contracts.

Behavioral: blocking-provider cancellation mid-flight (zero commit),
supersession, cancel_all reusability, terminal shutdown, and the
manual-search thread boundary (resolver runs on the worker, never the
caller).
"""

import threading
from pathlib import Path

from enrichment_fakes import (
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationState,
)
from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_executor import ThreadPoolEnrichmentExecutor
from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    EnrichmentExecutorPort,
    ExternalIdentityResolverPort,
    MusicBrainzKnowledgeProviderPort,
)
from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    KnowledgeProvenance,
)
from michi.domain.library import TrackRef, build_music_model


class HintResolver(ExternalIdentityResolverPort):
    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        return ()

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        return ()

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        return ()


class BlockingKnowledge(MusicBrainzKnowledgeProviderPort):
    """Blocks inside fetch_artist until released — deterministic
    mid-flight cancellation window."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def fetch_artist(self, local_artist_key, external_artist_id):
        self.entered.set()
        self.release.wait(timeout=10)
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )

    def artist_links(self, external_artist_id):
        return ArtistExternalLinks()

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        raise AssertionError("unused")


class BlockingExecutor(EnrichmentExecutorPort):
    """Single-thread real executor wrapper for cancellation tests."""

    def __init__(self):
        self._inner = ThreadPoolEnrichmentExecutor(max_workers=1)

    def submit(self, work) -> None:
        self._inner.submit(work)

    def shutdown(self, wait: bool = True) -> None:
        self._inner.shutdown(wait=wait)


class HintExtractorStub:
    def __init__(self, artist_hints=("mb-a",)):
        self._artist_hints = artist_hints

    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints(musicbrainz_artist_ids=tuple(self._artist_hints))


def make_coordinator(knowledge, executor=None, repository=None, identity_repo=None):
    repository = repository or RecordingKnowledgeRepository()
    identity_repo = identity_repo or InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=HintResolver(),
        artist_provider=None,
        album_provider=None,
        repository=repository,
        identity_repository=identity_repo,
    )
    coordinator = EnrichmentCoordinator(
        service=service,
        resolver=service._resolver,
        evidence_builder=LibraryEnrichmentEvidenceBuilder(HintExtractorStub()),
        mb_knowledge=knowledge,
        wikidata=None,
        wikipedia=None,
        commons=None,
        coverart=None,
        asset_store=None,
        executor=executor or BlockingExecutor(),
        transport=None,
        enabled=lambda: True,
    )
    return coordinator, service, repository, identity_repo


def _tracks():
    return (
        TrackRef(
            file_path=Path("/a.flac"),
            title="T1",
            artist="Artist A",
            album="Album X",
            year=1980,
            album_artist="Artist A",
        ),
    )


class TestCancellationMidFlight:
    def test_artist_cancel_blocks_commit(self):
        knowledge = BlockingKnowledge()
        coordinator, _, repository, _ = make_coordinator(
            knowledge, executor=BlockingExecutor()
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        done = threading.Event()

        def on_state(key, state):
            states.append(state)
            if state is EnrichmentOperationState.CANCELLED:
                done.set()

        coordinator.enrich_artist(model.artists[0], model.albums, tracks, on_state)
        assert knowledge.entered.wait(timeout=5)
        coordinator.cancel_artist("artist a")
        knowledge.release.set()
        assert done.wait(timeout=5)
        assert states[-1] is EnrichmentOperationState.CANCELLED
        assert repository.write_count == 0

    def test_superseded_operation_late_result_rejected(self):
        knowledge = BlockingKnowledge()
        coordinator, service, repository, _ = make_coordinator(
            knowledge, executor=BlockingExecutor()
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        first_states: list[EnrichmentOperationState] = []
        second_states: list[EnrichmentOperationState] = []
        second_done = threading.Event()

        def on_second(key, state):
            second_states.append(state)
            if state in (
                EnrichmentOperationState.READY,
                EnrichmentOperationState.PARTIAL,
                EnrichmentOperationState.FAILED,
                EnrichmentOperationState.CANCELLED,
            ):
                second_done.set()

        coordinator.enrich_artist(
            model.artists[0], model.albums, tracks, lambda k, s: first_states.append(s)
        )
        assert knowledge.entered.wait(timeout=5)
        # Supersession: a NEW operation on the same entity cancels A.
        coordinator.enrich_artist(model.artists[0], model.albums, tracks, on_second)
        knowledge.release.set()
        assert second_done.wait(timeout=5)
        coordinator._executor.shutdown(wait=True)
        # The superseded A never committed; B completed normally.
        assert repository.write_count == 1
        assert any(s is EnrichmentOperationState.CANCELLED for s in first_states)
        assert second_states[-1] in (
            EnrichmentOperationState.READY,
            EnrichmentOperationState.PARTIAL,
        )

    def test_cancel_all_then_new_operation_works(self):
        knowledge = BlockingKnowledge()
        coordinator, _, repository, _ = make_coordinator(
            knowledge, executor=BlockingExecutor()
        )
        coordinator.cancel_all()  # no active ops: pure no-op
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0], model.albums, tracks, lambda k, s: states.append(s)
        )
        knowledge.release.set()
        coordinator._executor.shutdown(wait=True)
        assert states[-1] is EnrichmentOperationState.READY
        assert repository.write_count == 1

    def test_shutdown_terminal_no_new_operations(self):
        coordinator, _, repository, _ = make_coordinator(
            BlockingKnowledge(), executor=BlockingExecutor()
        )
        coordinator.shutdown()
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0], model.albums, tracks, lambda k, s: states.append(s)
        )
        assert states == [EnrichmentOperationState.CANCELLED]
        assert repository.write_count == 0


class TestAsyncSearchThreadBoundary:
    def test_resolver_runs_on_worker_not_caller(self):
        """Behavioral proof: the resolver executes on the executor
        thread; the caller returns immediately (never blocked)."""
        caller_thread = threading.get_ident()
        resolver_threads: list[int] = []

        class RecordingResolver(ExternalIdentityResolverPort):
            def find_artist_candidates(self, evidence):
                resolver_threads.append(threading.get_ident())
                return ()

            def find_release_group_candidates(self, evidence):
                return ()

            def find_release_edition_candidates(self, evidence):
                return ()

        repository = RecordingKnowledgeRepository()
        service = EnrichmentService(
            resolver=HintResolver(),
            artist_provider=None,
            album_provider=None,
            repository=repository,
            identity_repository=InMemoryIdentityRepository(),
        )
        coordinator = EnrichmentCoordinator(
            service=service,
            resolver=RecordingResolver(),
            evidence_builder=LibraryEnrichmentEvidenceBuilder(HintExtractorStub()),
            mb_knowledge=BlockingKnowledge(),
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=BlockingExecutor(),
            transport=None,
            enabled=lambda: True,
        )
        received: list = []
        done = threading.Event()

        def on_result(views):
            received.append(views)
            done.set()

        coordinator.search_artist_candidates_async("Some Artist", on_result)
        assert done.wait(timeout=5)
        assert resolver_threads, "resolver never ran"
        assert resolver_threads[0] != caller_thread
        assert received == [()]
