"""M6.9-BACKEND-R1.1 — lifecycle: async failure convergence, linearizable
delivery, controlled async search.

- identity resolution transport failure -> OFFLINE terminal state
- identity resolution malformed payload -> FAILED terminal state
- unexpected worker exceptions -> FAILED + logged (never silent)
- cancellation vs delivery linearized (cancel-wins -> zero commit)
- superseded operation cannot commit at the pre-commit gate
- async search after shutdown -> controlled rejection (False), no
  RuntimeError, no network
- provider search failure -> error callback, never empty success
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
    EnrichmentProviderError,
    EnrichmentTransportError,
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


class FailingResolver(ExternalIdentityResolverPort):
    def __init__(self, error):
        self._error = error

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        raise self._error

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        raise self._error

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        raise self._error


class NoopKnowledge(MusicBrainzKnowledgeProviderPort):
    def fetch_artist(self, local_artist_key, external_artist_id):
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )

    def artist_links(self, external_artist_id):
        return ArtistExternalLinks()

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        raise AssertionError("unused")


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


class HintResolver(ExternalIdentityResolverPort):
    """Resolves ONLY from explicit hints (no network)."""

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        return ()

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        return ()

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        return ()


class HintExtractorStub:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints(
            musicbrainz_artist_ids=("mb-a",),
            musicbrainz_release_group_ids=("rg-x",),
        )


class NoHintsExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints()


def make_coordinator(resolver=None, knowledge=None, hintless=False):
    repository = RecordingKnowledgeRepository()
    identity_repo = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=resolver or HintResolver(),
        artist_provider=None,
        album_provider=None,
        repository=repository,
        identity_repository=identity_repo,
    )
    coordinator = EnrichmentCoordinator(
        service=service,
        resolver=service._resolver,
        evidence_builder=LibraryEnrichmentEvidenceBuilder(
            NoHintsExtractor() if hintless else HintExtractorStub()
        ),
        mb_knowledge=knowledge or NoopKnowledge(),
        wikidata=None,
        wikipedia=None,
        commons=None,
        coverart=None,
        asset_store=None,
        executor=ThreadPoolEnrichmentExecutor(max_workers=1),
        transport=None,
        enabled=lambda: True,
    )
    return coordinator, service, repository, identity_repo


def _run_artist(coordinator):
    model = build_music_model(_tracks())
    states: list[EnrichmentOperationState] = []
    done = threading.Event()

    def on_state(ev):
        states.append(ev.state)
        done.set()

    coordinator.enrich_artist(model.artists[0], model.albums, _tracks(), on_state)
    assert done.wait(timeout=10)
    coordinator._executor.shutdown(wait=True)
    return states


class TestAsyncFailureConvergence:
    def test_artist_identity_transport_failure_is_offline(self):
        coordinator, _, repository, identity_repo = make_coordinator(
            resolver=FailingResolver(EnrichmentTransportError("offline")),
            hintless=True,
        )
        states = _run_artist(coordinator)
        assert states[-1] is EnrichmentOperationState.OFFLINE
        assert repository.write_count == 0
        assert identity_repo.load_artist_identity("artist a") is None

    def test_album_identity_transport_failure_is_offline(self):
        coordinator, _, repository, _ = make_coordinator(
            resolver=FailingResolver(EnrichmentTransportError("offline")),
            hintless=True,
        )
        model = build_music_model(_tracks())
        states: list[EnrichmentOperationState] = []
        done = threading.Event()
        coordinator.enrich_album(
            model.albums[0],
            on_state=lambda ev: (states.append(ev.state), done.set()),
        )
        assert done.wait(timeout=10)
        coordinator._executor.shutdown(wait=True)
        assert states[-1] is EnrichmentOperationState.OFFLINE
        assert repository.write_count == 0

    def test_artist_identity_malformed_payload_is_failed(self):
        coordinator, _, repository, _ = make_coordinator(
            resolver=FailingResolver(EnrichmentProviderError("invalid JSON")),
            hintless=True,
        )
        states = _run_artist(coordinator)
        assert states[-1] is EnrichmentOperationState.FAILED
        assert repository.write_count == 0

    def test_unexpected_exception_is_failed_not_silent(self, caplog):
        class BoomError(Exception):
            pass

        coordinator, _, repository, _ = make_coordinator(
            resolver=FailingResolver(BoomError("programming error")),
            hintless=True,
        )
        states = _run_artist(coordinator)
        assert states[-1] is EnrichmentOperationState.FAILED
        assert repository.write_count == 0
        assert any(
            "unexpected artist enrichment failure" in r.message for r in caplog.records
        )


class TestLinearizableDelivery:
    def test_cancel_wins_pre_delivery_zero_commit(self):
        """Deterministic barrier race: cancel lands BEFORE the commit
        gate — the operation can never deliver."""
        coordinator, service, repository, _ = make_coordinator()
        model = build_music_model(_tracks())
        entered = threading.Event()
        release = threading.Event()
        states: list[EnrichmentOperationState] = []

        original = coordinator._mb.fetch_artist

        def blocking_fetch(*args, **kwargs):
            entered.set()
            release.wait(timeout=10)
            return original(*args, **kwargs)

        coordinator._mb.fetch_artist = blocking_fetch
        done = threading.Event()

        def on_state(ev):
            states.append(ev.state)
            if ev.state is EnrichmentOperationState.CANCELLED:
                done.set()

        coordinator.enrich_artist(model.artists[0], model.albums, _tracks(), on_state)
        assert entered.wait(timeout=10)
        coordinator.cancel_artist("artist a")
        release.set()
        assert done.wait(timeout=10)
        coordinator._executor.shutdown(wait=True)
        assert states[-1] is EnrichmentOperationState.CANCELLED
        assert repository.write_count == 0

    def test_superseded_operation_cannot_commit(self):
        coordinator, service, repository, _ = make_coordinator()
        model = build_music_model(_tracks())
        entered = threading.Event()
        release = threading.Event()
        original = coordinator._mb.fetch_artist

        def blocking_fetch(*args, **kwargs):
            entered.set()
            release.wait(timeout=10)
            return original(*args, **kwargs)

        coordinator._mb.fetch_artist = blocking_fetch
        first_states: list[EnrichmentOperationState] = []
        second_done = threading.Event()
        second_states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            _tracks(),
            lambda ev: first_states.append(ev.state),
        )
        assert entered.wait(timeout=10)
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            _tracks(),
            lambda ev: (second_states.append(ev.state), second_done.set()),
        )
        release.set()
        assert second_done.wait(timeout=10)
        coordinator._executor.shutdown(wait=True)
        # Superseded A: CANCELLED at the linearized gate, zero commit.
        assert any(s is EnrichmentOperationState.CANCELLED for s in first_states)
        assert second_states[-1] in (
            EnrichmentOperationState.READY,
            EnrichmentOperationState.PARTIAL,
        )
        assert repository.write_count == 1


class TestAsyncSearchControlledSubmission:
    def test_search_after_shutdown_rejected_without_runtime_error(self):
        coordinator, _, _, _ = make_coordinator()
        coordinator.shutdown()
        accepted = coordinator.search_artist_candidates_async(
            "Some Artist", on_result=lambda r: None
        )
        assert accepted is False
        accepted_album = coordinator.search_album_candidates_async(
            "Album", "", on_result=lambda r: None
        )
        assert accepted_album is False

    def test_normal_search_accepted_and_result_delivered(self):
        coordinator, _, _, _ = make_coordinator()
        received: list = []
        done = threading.Event()

        def on_result(views):
            received.append(views)
            done.set()

        accepted = coordinator.search_artist_candidates_async(
            "Some Artist", on_result=on_result
        )
        assert accepted is True
        assert done.wait(timeout=10)
        assert len(received) == 1  # exactly once
        coordinator._executor.shutdown(wait=True)

    def test_provider_failure_goes_to_error_callback(self):
        coordinator, _, _, _ = make_coordinator(
            resolver=FailingResolver(EnrichmentProviderError("provider broke"))
        )
        results: list = []
        errors: list = []
        done = threading.Event()

        def on_result(views):
            results.append(views)
            done.set()

        def on_error(exc):
            errors.append(exc)
            done.set()

        coordinator.search_artist_candidates_async(
            "Some Artist", on_result=on_result, on_error=on_error
        )
        assert done.wait(timeout=10)
        assert results == []  # never an empty success
        assert len(errors) == 1
        coordinator._executor.shutdown(wait=True)
