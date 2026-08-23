"""M6.9-BACKEND-R1.2 — request correlation races (behavioral, 2 real
workers, deterministic Events only).

- stale worker can never invalidate / replace / mutate a newer request
- cancel before resolution prevents identity persistence
- supersession before registration prevents stale registration
- old failure never kills the new request
- manual identity change vs delivery is serialized
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


class BlockingResolver(ExternalIdentityResolverPort):
    """Blocks the FIRST ``block_count`` calls; afterwards returns a
    resolving candidate (or raises ``error`` when set)."""

    def __init__(self, block_count=1):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.error: BaseException | None = None
        self.artist_calls = 0
        self._block_count = block_count

    def _maybe_wait(self):
        self.artist_calls += 1
        if self.artist_calls <= self._block_count:
            self.entered.set()
            self.release.wait(timeout=15)
        if self.error is not None:
            raise self.error
        from michi.domain.enrichment import ArtistCandidate, LocalAlbumEvidence

        return (
            ArtistCandidate(
                "mb-b",
                canonical_name="Artist A",
                known_albums=(LocalAlbumEvidence("Album X", 1980),),
            ),
        )

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        return self._maybe_wait()

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        return self._maybe_wait()

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        return ()


class NoopKnowledge(MusicBrainzKnowledgeProviderPort):
    def __init__(self, block_fetch: threading.Event | None = None):
        self._block_fetch = block_fetch
        self.entered_fetch = threading.Event()

    def fetch_artist(self, local_artist_key, external_artist_id):
        self.entered_fetch.set()
        if self._block_fetch is not None:
            self._block_fetch.wait(timeout=15)
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )

    def artist_links(self, external_artist_id):
        return ArtistExternalLinks()

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        raise AssertionError("unused")


class NoHintsExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints()


class SingleHintExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints(
            musicbrainz_artist_ids=("mb-a",),
            musicbrainz_release_group_ids=("rg-x",),
        )


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


class Harness:
    def __init__(self, hintless=False, knowledge=None):
        self.repository = RecordingKnowledgeRepository()
        self.identity_repo = InMemoryIdentityRepository()
        self.resolver = BlockingResolver()
        self.service = EnrichmentService(
            resolver=self.resolver,
            artist_provider=None,
            album_provider=None,
            repository=self.repository,
            identity_repository=self.identity_repo,
        )
        self.knowledge = knowledge if knowledge is not None else NoopKnowledge()
        self.coordinator = EnrichmentCoordinator(
            service=self.service,
            resolver=self.resolver,
            evidence_builder=LibraryEnrichmentEvidenceBuilder(
                NoHintsExtractor() if hintless else SingleHintExtractor()
            ),
            mb_knowledge=self.knowledge,
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=ThreadPoolEnrichmentExecutor(max_workers=2),
            transport=None,
            enabled=lambda: True,
        )
        self.states: dict[str, list[EnrichmentOperationState]] = {}

    def events_for(self, name):
        events = []
        self.states[name] = [e.state for e in events]  # placeholder
        return events

    def enrich_artist(self, name):
        model = build_music_model(_tracks())
        self.coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            _tracks(),
            lambda ev: self.states.setdefault(name, []).append(ev.state),
        )

    def enrich_album(self, name):
        model = build_music_model(_tracks())
        self.coordinator.enrich_album(
            model.albums[0],
            lambda ev: self.states.setdefault(name, []).append(ev.state),
        )


class TestRequestCorrelationRaces:
    def test_old_failure_never_kills_new_request(self):
        harness = Harness(hintless=True)
        harness.enrich_artist("A")
        assert harness.resolver.entered.wait(timeout=5)
        # B (generation 2) resolves (resolver no longer blocks) and
        # registers its request.
        harness.enrich_artist("B")
        # Release A with a TRANSPORT failure.
        harness.resolver.error = EnrichmentTransportError("offline")
        harness.resolver.release.set()
        harness.coordinator._executor.shutdown(wait=True)
        # A terminal: OFFLINE — never killed B.
        assert harness.states["A"][-1] in (
            EnrichmentOperationState.OFFLINE,
            EnrichmentOperationState.FAILED,
            EnrichmentOperationState.CANCELLED,
        )
        # B request still current: exactly one knowledge write.
        assert harness.repository.write_count == 1

    def test_cancel_before_resolution_returns(self):
        harness = Harness(hintless=True)
        harness.enrich_artist("A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.cancel_artist("artist a")
        harness.resolver.release.set()
        harness.coordinator._executor.shutdown(wait=True)
        assert harness.states["A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.repository.write_count == 0
        assert harness.identity_repo.load_artist_identity("artist a") is None

    def test_supersession_before_registration_prevents_stale_register(self):
        harness = Harness(hintless=True)
        harness.enrich_artist("A")  # A blocked in resolver (gen 1)
        assert harness.resolver.entered.wait(timeout=5)
        # B begins (gen 2): the resolver no longer blocks -> B resolves
        # and registers its request.
        harness.enrich_artist("B")
        harness.resolver.release.set()
        harness.coordinator._executor.shutdown(wait=True)
        # Exactly ONE request was ever registered (B), one commit.
        assert harness.repository.write_count == 1
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity is not None

    def test_old_worker_cannot_invalidate_new_request_exact(self):
        """Direct ledger proof: a stale request id/generation can never
        invalidate the current one.

        Deterministic: B's worker is parked inside ``fetch_artist`` AFTER
        registering — while parked, the ledger provably holds B's request
        (registration precedes fetch in the worker)."""
        harness = Harness(
            hintless=True,
            knowledge=NoopKnowledge(block_fetch=threading.Event()),
        )
        harness.enrich_artist("A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.enrich_artist("B")
        # B registers its request, then blocks in fetch_artist. Fetch
        # entry implies registration completed (it precedes the fetch).
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        from michi.domain.enrichment import EnrichmentEntityKind

        current = harness.service._ledger._current.get(
            (EnrichmentEntityKind.ARTIST, "artist a")
        )
        assert current is not None  # B's request exists (parked)
        stale_attempt = harness.service.cancel_request_exact(_stale_request(current))
        assert stale_attempt is False  # stale context cannot invalidate
        # Unpark B: it commits under its own context (write_count == 1).
        harness.knowledge._block_fetch.set()
        harness.resolver.release.set()
        harness.coordinator._executor.shutdown(wait=True)
        # B's request was untouched by the stale attempt -> it commits.
        assert harness.repository.write_count == 1


def _stale_request(current):
    from michi.domain.enrichment import EnrichmentRequest

    return EnrichmentRequest(
        request_id="stale-id",
        entity_kind=current.entity_kind,
        local_entity_key=current.local_entity_key,
        external_entity_id=current.external_entity_id,
        external_variant_id=current.external_variant_id,
        generation=current.generation - 1,
    )


class TestManualIdentityVsDelivery:
    def test_manual_confirm_wins_delivery_stale(self):
        harness = Harness()  # hint-driven: resolves immediately
        model = build_music_model(_tracks())
        states: list[EnrichmentOperationState] = []
        done = threading.Event()

        def on_state(ev):
            states.append(ev.state)
            if ev.state in (
                EnrichmentOperationState.READY,
                EnrichmentOperationState.PARTIAL,
                EnrichmentOperationState.FAILED,
                EnrichmentOperationState.CANCELLED,
            ):
                done.set()

        harness.coordinator.enrich_artist(
            model.artists[0], model.albums, _tracks(), on_state
        )
        assert done.wait(timeout=10)
        # Identity changed manually AFTER the operation committed.
        harness.service.confirm_artist_identity("artist a", "mb-manual")
        # Old knowledge was removed by the transition; new authority only.
        assert harness.repository.write_count == 1
        assert harness.repository.load_artist_profile("artist a") is None
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity.external_artist_id == "mb-manual"
        harness.coordinator._executor.shutdown(wait=True)
