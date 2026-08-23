"""M6.9-BACKEND-R1.3 — final authority barrier + resurrection prevention
seal.

Deterministic concurrency matrix (§37): threading.Event/Barrier only,
TWO real executor workers for the coordinator races, zero sleeps. Tests
exercise the PUBLIC application surface (begin_operation /
retire_operation / request / deliver / confirm / reset / clear / cancel)
— the ledger internals are probed only through the dedicated unit test
(test_invalidate_if_generation_current_ledger_unit).

Covered invariants:
- manual confirm beats an in-flight AUTO result (P0)
- MANUAL can never be downgraded by a late AUTO/EMBEDDED operation
- reset / clear_identities kill every in-flight result (resurrection seal)
- album artist-dependency revalidation (FIX-07): A -> B / reset -> STALE
- old-failure-vs-new-request, both entity kinds
- delivery races in BOTH orders, artist and album
- retire_operation barrier semantics + strictly monotonic generations
- cancel_all SNAPSHOT semantics: ops active at the snapshot die, ops
  started after the snapshot survive
- public cancel race, shutdown admission race (2 real workers)
"""

import threading
from pathlib import Path

from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
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
    ExternalIdentityResolverPort,
    MusicBrainzKnowledgeProviderPort,
)
from michi.application.enrichment_service import (
    DeliveryVerdict,
    EnrichmentService,
)
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistCandidate,
    ArtistExternalLinks,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    ArtistKnowledgeProfile,
    EnrichmentEntityKind,
    EnrichmentRequest,
    EnrichmentRequestLedger,
    IdentityResolutionStatus,
    KnowledgeProvenance,
    LocalAlbumEvidence,
    MatchMethod,
)

# ----------------------------------------------------------------------
# shared evidence helpers
# ----------------------------------------------------------------------


def artist_evidence(name="Artist A", mbids=()):
    return ArtistIdentityEvidence(
        local_artist_key=name.casefold(),
        local_artist_name=name,
        identity_hints=ArtistIdentityHints(artist_ids=tuple(mbids)),
    )


def album_evidence(key="album-a", rg_ids=(), release_ids=(), artist_key=""):
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title="Album X",
        local_album_artist_key=artist_key,
        local_album_artist_name="Artist A" if artist_key else "",
        identity_hints=AlbumIdentityHints(
            release_group_ids=tuple(rg_ids), release_ids=tuple(release_ids)
        ),
    )


def make_service():
    repository = RecordingKnowledgeRepository()
    identity_repository = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=FakeIdentityResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=repository,
        identity_repository=identity_repository,
    )
    return service, repository, identity_repository


# ----------------------------------------------------------------------
# service-level: manual / reset / clear barriers (P0 + resurrection seal)
# ----------------------------------------------------------------------


class TestManualAuthorityBarrier:
    def test_manual_confirm_beats_inflight_auto(self):
        """P0: a MANUAL confirm while an AUTO operation is in flight makes
        the late AUTO result STALE with zero knowledge writes."""
        service, repository, identity_repo = make_service()
        gen = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-auto",)), generation=gen
        )
        assert outcome.request is not None
        assert outcome.resolution.status is IdentityResolutionStatus.RESOLVED

        service.confirm_artist_identity("artist a", "mb-manual")

        profile = service._artist_provider.fetch_profile("artist a", "mb-auto")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        identity = identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL

    def test_manual_never_downgraded_by_late_auto(self):
        """§51-53: a late AUTO/EMBEDDED operation — even carrying a
        DIFFERENT external id — short-circuits against the MANUAL
        identity and can never replace it."""
        service, _, identity_repo = make_service()
        service.confirm_artist_identity("artist a", "mb-manual")

        gen = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-auto-other",)),
            generation=gen,
        )
        # Short-circuit: the request carries the MANUAL id.
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-manual"
        identity = identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL
        assert identity.external_artist_id == "mb-manual"

    def test_manual_album_never_downgraded_by_late_auto(self):
        service, _, identity_repo = make_service()
        service.confirm_album_identity("album-a", "rg-manual", release_id="rel-m")
        gen = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-auto",)), generation=gen
        )
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "rg-manual"
        identity = identity_repo.load_album_identity("album-a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL


class TestResurrectionPreventionSeal:
    def test_reset_kills_inflight_artist(self):
        service, repository, identity_repo = make_service()
        gen = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen
        )
        service.reset_artist_identity("artist a")
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        assert identity_repo.load_artist_identity("artist a") is None

    def test_reset_then_new_generation_resolves_fresh(self):
        """A reset seals the old generation; the NEXT generation resolves
        and commits normally (resurrection of the OLD result is
        impossible, the new operation is unaffected)."""
        service, repository, identity_repo = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome1 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-old",)), generation=gen1
        )
        service.reset_artist_identity("artist a")
        assert (
            service.deliver_artist_profile(
                outcome1.request,
                service._artist_provider.fetch_profile("artist a", "mb-old"),
            )
            is DeliveryVerdict.STALE
        )

        gen2 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        assert gen2 > gen1  # strictly monotonic authority
        outcome2 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-new",)), generation=gen2
        )
        assert outcome2.request is not None
        assert (
            service.deliver_artist_profile(
                outcome2.request,
                service._artist_provider.fetch_profile("artist a", "mb-new"),
            )
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1

    def test_clear_identities_kills_every_inflight_result(self):
        """clear_identities bumps EVERY known generation epoch: any late
        result of any entity is STALE, zero writes, identities gone."""
        service, repository, identity_repo = make_service()
        service.confirm_artist_identity("artist a", "mb-manual")
        service.confirm_album_identity("album-a", "rg-manual")
        gen_a = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        gen_b = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome_a = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-manual",)), generation=gen_a
        )
        outcome_b = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-manual",)), generation=gen_b
        )
        assert outcome_a.request is not None and outcome_b.request is not None

        service.clear_identities()

        assert (
            service.deliver_artist_profile(
                outcome_a.request,
                service._artist_provider.fetch_profile("artist a", "mb-manual"),
            )
            is DeliveryVerdict.STALE
        )
        assert (
            service.deliver_album_profile(
                outcome_b.request,
                service._album_provider.fetch_profile("album-a", "rg-manual"),
            )
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        assert identity_repo.load_artist_identity("artist a") is None
        assert identity_repo.load_album_identity("album-a") is None


class TestAlbumArtistDependencyRevalidation:
    """FIX-07: an album that resolved through its artist identity
    revalidates that dependency under the authority lock before commit."""

    def _inflight_album(self, service):
        gen = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-x",), artist_key="artist a"),
            generation=gen,
        )
        assert outcome.request is not None
        assert outcome.request.artist_dependency_id == "mb-a"
        return outcome

    def test_artist_a_to_b_makes_inflight_album_stale(self):
        service, repository, _ = make_service()
        service.confirm_artist_identity("artist a", "mb-a")
        outcome = self._inflight_album(service)

        service.confirm_artist_identity("artist a", "mb-b")

        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_artist_reset_makes_inflight_album_stale(self):
        service, repository, _ = make_service()
        service.confirm_artist_identity("artist a", "mb-a")
        outcome = self._inflight_album(service)

        service.reset_artist_identity("artist a")

        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_artist_unchanged_album_commits(self):
        """Control: with the dependency still current the album commits."""
        service, repository, _ = make_service()
        service.confirm_artist_identity("artist a", "mb-a")
        outcome = self._inflight_album(service)

        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1


# ----------------------------------------------------------------------
# delivery races, BOTH orders, BOTH entity kinds
# ----------------------------------------------------------------------


class TestDeliveryRaces:
    def test_artist_supersede_then_deliver_is_stale(self):
        service, repository, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome1 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen1
        )
        gen2 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome2 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen2
        )
        assert outcome2.request is not None
        assert (
            service.deliver_artist_profile(
                outcome1.request,
                service._artist_provider.fetch_profile("artist a", "mb-a"),
            )
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_artist_deliver_then_supersede_commits_exactly_once(self):
        service, repository, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome1 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen1
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome1.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        # A second delivery of the SAME request can never commit again.
        assert (
            service.deliver_artist_profile(outcome1.request, profile)
            is DeliveryVerdict.UNKNOWN
        )
        # Superseding afterwards changes nothing: exactly one write.
        service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        assert repository.write_count == 1
        assert repository.load_artist_profile("artist a") is not None

    def test_album_supersede_then_deliver_is_stale(self):
        service, repository, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome1 = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",)), generation=gen1
        )
        gen2 = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome2 = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",)), generation=gen2
        )
        assert outcome2.request is not None
        assert (
            service.deliver_album_profile(
                outcome1.request,
                service._album_provider.fetch_profile("album-a", "rg-a"),
            )
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_old_failure_cannot_kill_new_artist_request(self):
        """§30: deliver_artist_failure from a superseded generation is
        STALE — the new request survives and commits."""
        service, repository, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome1 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen1
        )
        gen2 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome2 = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen2
        )
        assert outcome2.request is not None
        assert (
            service.deliver_artist_failure(outcome1.request)
            is DeliveryVerdict.STALE
        )
        assert (
            service.deliver_artist_profile(
                outcome2.request,
                service._artist_provider.fetch_profile("artist a", "mb-a"),
            )
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1

    def test_old_failure_cannot_kill_new_album_request(self):
        service, repository, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome1 = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",)), generation=gen1
        )
        gen2 = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome2 = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",)), generation=gen2
        )
        assert outcome2.request is not None
        assert (
            service.deliver_album_failure(outcome1.request)
            is DeliveryVerdict.STALE
        )
        assert (
            service.deliver_album_profile(
                outcome2.request,
                service._album_provider.fetch_profile("album-a", "rg-a"),
            )
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1


# ----------------------------------------------------------------------
# epoch barrier + monotonicity
# ----------------------------------------------------------------------


class TestEpochBarriers:
    def test_retire_operation_stale_generation_returns_false(self):
        service, _, _ = make_service()
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        gen2 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        # A stale retire (older generation) is a no-op barrier.
        assert (
            service.retire_operation(
                EnrichmentEntityKind.ARTIST, "artist a", gen1
            )
            is False
        )
        # The CURRENT generation retires and invalidates its request.
        assert (
            service.retire_operation(
                EnrichmentEntityKind.ARTIST, "artist a", gen2
            )
            is True
        )

    def test_retire_then_delivery_is_stale(self):
        service, repository, _ = make_service()
        gen = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=gen
        )
        assert (
            service.retire_operation(EnrichmentEntityKind.ARTIST, "artist a", gen)
            is True
        )
        assert (
            service.deliver_artist_profile(
                outcome.request,
                service._artist_provider.fetch_profile("artist a", "mb-a"),
            )
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_next_generation_strictly_monotonic(self):
        service, _, _ = make_service()
        generations = [
            service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
            for _ in range(3)
        ]
        assert generations == sorted(set(generations))
        assert all(
            generations[i] < generations[i + 1]
            for i in range(len(generations) - 1)
        )


class TestLedgerGenerationInvalidationUnit:
    def test_invalidate_if_generation_current_ledger_unit(self):
        """The ONLY test that probes ledger internals directly — the
        generation-scoped invalidation helper used by retire_operation."""
        ledger = EnrichmentRequestLedger()
        request = EnrichmentRequest(
            request_id="req-1",
            entity_kind=EnrichmentEntityKind.ARTIST,
            local_entity_key="artist a",
            external_entity_id="mb-a",
            generation=1,
        )
        ledger.register(request)
        # Same-generation invalidation wins.
        assert ledger.invalidate_if_generation_current(
            EnrichmentEntityKind.ARTIST, "artist a", 1
        )
        assert ledger.deliver(request) is DeliveryVerdict.STALE

        # A newer request is NEVER invalidated by an older generation.
        request2 = EnrichmentRequest(
            request_id="req-2",
            entity_kind=EnrichmentEntityKind.ARTIST,
            local_entity_key="artist a",
            external_entity_id="mb-a",
            generation=2,
        )
        ledger.register(request2)
        assert not ledger.invalidate_if_generation_current(
            EnrichmentEntityKind.ARTIST, "artist a", 1
        )
        assert ledger.deliver(request2) is DeliveryVerdict.COMMITTED


# ----------------------------------------------------------------------
# coordinator races (2 REAL workers, Events only)
# ----------------------------------------------------------------------


class GateResolver(ExternalIdentityResolverPort):
    """Blocks the first ``block_count`` resolver calls; afterwards
    returns a resolvable candidate (or raises ``error`` when set)."""

    def __init__(self, block_count=1):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.error: BaseException | None = None
        self.calls = 0
        self._block_count = block_count

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        self.calls += 1
        if self.calls <= self._block_count:
            self.entered.set()
            self.release.wait(timeout=15)
        if self.error is not None:
            raise self.error
        return (
            ArtistCandidate(
                "mb-resolved",
                canonical_name=evidence.local_artist_name,
                known_albums=(LocalAlbumEvidence("Album X", 1980),),
            ),
        )

    def find_release_group_candidates(self, evidence):
        return ()

    def find_release_edition_candidates(self, evidence):
        return ()


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


class CoordinatorHarness:
    def __init__(self, resolver_block_count=1):
        self.repository = RecordingKnowledgeRepository()
        self.identity_repo = InMemoryIdentityRepository()
        self.resolver = GateResolver(block_count=resolver_block_count)
        self.service = EnrichmentService(
            resolver=self.resolver,
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=self.repository,
            identity_repository=self.identity_repo,
        )
        self.coordinator = EnrichmentCoordinator(
            service=self.service,
            resolver=self.resolver,
            evidence_builder=LibraryEnrichmentEvidenceBuilder(
                _NoHintsExtractor()
            ),
            mb_knowledge=NoopKnowledge(),
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
        self.terminal: dict[str, threading.Event] = {}

    def enrich_artist(self, name):
        # Pre-create the terminal signal: the worker wakes asynchronously,
        # so the test must be able to wait on the Event BEFORE the
        # terminal state is reported.
        self.terminal.setdefault(name, threading.Event())
        model = _single_artist_model(name)

        def on_state(event):
            terminal = event.state in {
                EnrichmentOperationState.READY,
                EnrichmentOperationState.PARTIAL,
                EnrichmentOperationState.FAILED,
                EnrichmentOperationState.OFFLINE,
                EnrichmentOperationState.CANCELLED,
                EnrichmentOperationState.NOT_FOUND,
                EnrichmentOperationState.AMBIGUOUS,
            }
            self.states.setdefault(name, []).append(event.state)
            if terminal:
                self.terminal.setdefault(name, threading.Event()).set()

        self.coordinator.enrich_artist(
            model.artists[0], model.albums, model.tracks, on_state
        )

    @property
    def write_count(self) -> int:
        return self.repository.write_count


def _single_artist_model(name):
    from michi.domain.library import AlbumRef, ArtistRef, TrackRef

    tracks = (
        TrackRef(
            file_path=Path("/a.flac"),
            title="T1",
            artist=name,
            album="Album X",
            year=1980,
            album_artist=name,
        ),
    )
    return _Model(
        artists=(
            ArtistRef(
                key=name.casefold(),
                name=name,
                track_count=1,
                album_count=1,
            ),
        ),
        albums=(
            AlbumRef(
                key="album-x",
                title="Album X",
                artist=name,
                track_count=1,
                duration_ms=240000,
                track_paths=(Path("/a.flac"),),
                year=1980,
            ),
        ),
        tracks=tracks,
    )


class _Model:
    def __init__(self, artists, albums, tracks):
        self.artists = artists
        self.albums = albums
        self.tracks = tracks


class _NoHintsExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints()


class TestCoordinatorRaces:
    def test_cancel_all_snapshot_semantics(self):
        """Operations ACTIVE at the snapshot are retired; an operation
        started AFTER the snapshot survives and completes."""
        harness = CoordinatorHarness(resolver_block_count=2)
        harness.enrich_artist("Artist A")
        harness.enrich_artist("Artist B")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.cancel_all()
        harness.enrich_artist("Artist C")
        # A and B wake, see their retired generations, report CANCELLED;
        # C (started AFTER the snapshot) runs to READY — deterministically
        # wait for its terminal event BEFORE shutdown so the executor can
        # never drop it.
        harness.resolver.release.set()
        assert harness.terminal["Artist C"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.states["Artist B"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.states["Artist C"][-1] is EnrichmentOperationState.READY
        # Only C committed knowledge.
        assert harness.write_count == 1

    def test_public_cancel_race(self):
        """A public cancel while the worker is mid-resolution retires the
        generation: the worker's result is SUPERSEDED, zero writes."""
        harness = CoordinatorHarness()
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.cancel_artist("artist a")
        harness.resolver.release.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        assert harness.identity_repo.load_artist_identity("artist a") is None

    def test_shutdown_admission_semantics(self):
        """Shutdown retires the in-flight generation BEFORE the executor
        waits; any operation submitted afterwards is rejected."""
        harness = CoordinatorHarness()
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        harness.coordinator.shutdown()
        harness.enrich_artist("Artist B")  # admitted? NO — after shutdown.

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.states["Artist B"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0

    def test_manual_confirm_wins_inflight_delivery(self):
        """Coordinator-level P0: a MANUAL confirm during a worker's
        in-flight AUTO operation retires it — CANCELLED, zero writes,
        MANUAL identity persisted."""
        harness = CoordinatorHarness()
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.service.confirm_artist_identity("artist a", "mb-manual")
        harness.resolver.release.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL
