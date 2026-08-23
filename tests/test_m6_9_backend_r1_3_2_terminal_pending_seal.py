"""M6.9-BACKEND-R1.3.2 — Final Terminal + Pending Request Seal.

Deterministic tests only (threading.Event, real threads, ZERO sleeps;
timeouts are safety bounds). Every regression test documents
WHY THIS FAILED ON R1.3.1 and was verified RED against the R1.3.1
behavior before the fix.

P1-01 — a LATE provider failure from an operation that already lost
authority (cancel / manual confirm / reset / supersession) must
converge to CANCELLED — never OFFLINE, never FAILED. Current
operations keep OFFLINE (transient) / FAILED (non-transient).

P1-02 — a NEW begin immediately supersedes the previous pending
request of that entity (under the same authority lock): no zombie
pending request can outlive the operation that produced it.
"""

import threading
import time
from pathlib import Path

from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)
from test_m6_9_backend_r1_3_1_atomicity_seal import GatedBeginService

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationState,
)
from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_executor import ThreadPoolEnrichmentExecutor
from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    EnrichmentTransportError,
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
    IdentityResolutionStatus,
    KnowledgeProvenance,
    LocalAlbumEvidence,
    MatchMethod,
    ReleaseGroupCandidate,
)


def artist_evidence(name="Artist A", mbids=(), with_albums=False):
    known = (LocalAlbumEvidence("Album X", 1980),) if with_albums else ()
    return ArtistIdentityEvidence(
        local_artist_key=name.casefold(),
        local_artist_name=name,
        known_albums=known,
        identity_hints=ArtistIdentityHints(artist_ids=tuple(mbids)),
    )


def album_evidence(key="album-a", rg_ids=(), release_ids=()):
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title="Album X",
        identity_hints=AlbumIdentityHints(
            release_group_ids=tuple(rg_ids), release_ids=tuple(release_ids)
        ),
    )


def make_service(resolver=None):
    repository = RecordingKnowledgeRepository()
    identity_repository = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=repository,
        identity_repository=identity_repository,
    )
    return service, repository, identity_repository


# ----------------------------------------------------------------------
# coordinator harness (worker-level races)
# ----------------------------------------------------------------------


class GateResolver(ExternalIdentityResolverPort):
    """Blocks the first ``block_count`` resolver calls; afterwards
    returns resolvable candidates."""

    def __init__(self, block_count=1, artists=True):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self._block_count = block_count
        self._artists = artists

    def _maybe_wait(self):
        self.calls += 1
        if self.calls <= self._block_count:
            self.entered.set()
            self.release.wait(timeout=15)

    def find_artist_candidates(self, evidence):
        self._maybe_wait()
        return (
            ArtistCandidate(
                "mb-resolved",
                canonical_name=evidence.local_artist_name,
                known_albums=(LocalAlbumEvidence("Album X", 1980),),
            ),
        )

    def find_release_group_candidates(self, evidence):
        self._maybe_wait()
        return (
            ReleaseGroupCandidate(
                release_group_id="rg-x",
                title=evidence.local_album_title,
                artist_credit_names=(evidence.local_album_artist_name,),
            ),
        )

    def find_release_edition_candidates(self, evidence):
        return ()


class _NoopKnowledge(MusicBrainzKnowledgeProviderPort):
    def fetch_artist(self, local_artist_key, external_artist_id):
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )

    def artist_links(self, external_artist_id):
        return ArtistExternalLinks()

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        return ArtistKnowledgeProfile(
            local_artist_key=local_album_key,
            external_artist_id=release_group_id,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )


class GatedKnowledge(_NoopKnowledge):
    """Blocks the FIRST fetch call; when released it raises ``error``
    (when configured). Later calls return normal profiles."""

    def __init__(self, error: BaseException | None = None):
        self.error = error
        self.entered_fetch = threading.Event()
        self.release_fetch = threading.Event()
        self.calls = 0

    def _gate(self):
        self.calls += 1
        first = self.calls == 1
        if first:
            self.entered_fetch.set()
            self.release_fetch.wait(timeout=15)
        if first and self.error is not None:
            raise self.error

    def fetch_artist(self, local_artist_key, external_artist_id):
        self._gate()
        return super().fetch_artist(local_artist_key, external_artist_id)

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        self._gate()
        return super().fetch_release_group(
            local_album_key, release_group_id, release_id
        )


class _NoHintsExtractor:
    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints()


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
    return (
        (ArtistRef(key=name.casefold(), name=name, track_count=1, album_count=1),),
        (
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
        tracks,
    )


class CoordinatorHarness:
    def __init__(self, knowledge=None):
        self.repository = RecordingKnowledgeRepository()
        self.identity_repo = InMemoryIdentityRepository()
        self.resolver = GateResolver()
        self.service = EnrichmentService(
            resolver=self.resolver,
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=self.repository,
            identity_repository=self.identity_repo,
        )
        self.knowledge = knowledge if knowledge is not None else _NoopKnowledge()
        self.coordinator = EnrichmentCoordinator(
            service=self.service,
            resolver=self.resolver,
            evidence_builder=LibraryEnrichmentEvidenceBuilder(_NoHintsExtractor()),
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
        self.terminal: dict[str, threading.Event] = {}

    def enrich_artist(self, name, label=None):
        """``label`` separates the state bucket from the artist name:
        two operations on the SAME entity (same name/key) can be tracked
        independently (used by the old-failure-vs-new-request test)."""
        label = label or name
        self.terminal.setdefault(label, threading.Event())
        artists, albums, tracks = _single_artist_model(name)
        self.coordinator.enrich_artist(
            artists[0], albums, tracks, self._on_state(label)
        )

    def enrich_album(self, name):
        self.terminal.setdefault(name, threading.Event())
        _, albums, _ = _single_artist_model(name)
        self.coordinator.enrich_album(albums[0], on_state=self._on_state(name))

    def _on_state(self, name):
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
                self.terminal[name].set()

        return on_state

    @property
    def write_count(self) -> int:
        return self.repository.write_count

    def current_token(self, entity_kind, local_key):
        return self.coordinator._operations.get((entity_kind, local_key))


# ----------------------------------------------------------------------
# P1-01 — late errors from obsolete operations must be CANCELLED
# ----------------------------------------------------------------------


class TestLateFailureAfterCancellation:
    def test_artist_cancelled_then_transient_failure_is_cancelled(self):
        """WHY THIS FAILED ON R1.3.1: _terminal_failure classified the
        exception (transient -> OFFLINE) WITHOUT checking whether the
        operation had already lost authority — a worker woken after a
        MANUAL confirm surfaced a network failure to the UI even though
        its generation was dead."""
        harness = CoordinatorHarness(
            knowledge=GatedKnowledge(error=EnrichmentTransportError("offline"))
        )
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        # Worker registered request A and is parked in the provider fetch.
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        harness.coordinator.confirm_artist_identity("artist a", "mb-manual")
        token = harness.current_token(EnrichmentEntityKind.ARTIST, "artist a")
        assert token is not None and token.cancelled is True
        harness.knowledge.release_fetch.set()  # provider wakes with a transient error
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert EnrichmentOperationState.OFFLINE not in harness.states["Artist A"]
        assert EnrichmentOperationState.FAILED not in harness.states["Artist A"]
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL
        assert harness.write_count == 0
        assert harness.service.pending_count() == 0

    def test_album_reset_then_transient_failure_is_cancelled(self):
        """WHY THIS FAILED ON R1.3.1: same classification bug on the
        album path — a reset (or manual confirm) followed by a late
        transient provider error surfaced OFFLINE and could not
        resurrect the deleted Album identity."""
        harness = CoordinatorHarness(
            knowledge=GatedKnowledge(error=EnrichmentTransportError("offline"))
        )
        harness.enrich_album("Album A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        harness.coordinator.reset_album_identity("album-x")
        token = harness.current_token(EnrichmentEntityKind.ALBUM, "album-x")
        assert token is not None and token.cancelled is True
        harness.knowledge.release_fetch.set()
        assert harness.terminal["Album A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Album A"][-1] is EnrichmentOperationState.CANCELLED
        assert EnrichmentOperationState.OFFLINE not in harness.states["Album A"]
        assert EnrichmentOperationState.FAILED not in harness.states["Album A"]
        assert harness.identity_repo.load_album_identity("album-x") is None
        assert harness.write_count == 0
        assert harness.service.pending_count() == 0

    def test_control_current_transient_failure_is_offline(self):
        """CONTROL: a CURRENT operation with a transient provider error
        still converges to OFFLINE — the fix never masks live errors."""
        harness = CoordinatorHarness(
            knowledge=GatedKnowledge(error=EnrichmentTransportError("offline"))
        )
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        harness.knowledge.release_fetch.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.OFFLINE
        assert harness.write_count == 0

    def test_control_current_non_transient_failure_is_failed(self):
        """CONTROL: a CURRENT operation with a non-transient provider
        error still converges to FAILED."""
        harness = CoordinatorHarness(
            knowledge=GatedKnowledge(error=EnrichmentProviderError("boom"))
        )
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        harness.knowledge.release_fetch.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.FAILED
        assert harness.write_count == 0


# ----------------------------------------------------------------------
# P1-02 — new begin immediately supersedes previous pending request
# ----------------------------------------------------------------------


class TestPendingRequestSupersededByNewBegin:
    def test_new_begin_retires_old_pending_request(self):
        """WHY THIS FAILED ON R1.3.1: begin_operation advanced the
        generation but left the previous request registered in the
        ledger — if the new operation failed before registering its own
        request, the old one stayed pending (pending_count == 1) with no
        live operation able to deliver it."""

        class ResolveOnceResolver(FakeIdentityResolver):
            """Resolves the first request (AUTO), then yields no
            candidates so the next operation fails before registering."""

            def __init__(self):
                super().__init__(
                    artists=(
                        ArtistCandidate(
                            "mb-a",
                            canonical_name="Artist A",
                            known_albums=(LocalAlbumEvidence("Album X", 1980),),
                        ),
                    )
                )
                self.calls = 0

            def find_artist_candidates(self, evidence):
                self.calls += 1
                return self._artists if self.calls == 1 else ()

        service, repository, _ = make_service(resolver=ResolveOnceResolver())
        gen1 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        outcome_a = service.request_artist_enrichment(
            artist_evidence(name="Artist A", with_albums=True), generation=gen1
        )
        assert outcome_a.request is not None
        assert service.pending_count() == 1

        # Operation B begins (generation 2): request A is IMMEDIATELY
        # superseded — no waiting for worker A to come back.
        gen2 = service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a")
        assert gen2 > gen1
        assert service.pending_count() == 0

        # B fails BEFORE registering its own request (resolver ran out
        # of candidates -> NO_MATCH): nothing remains pending.
        outcome_b = service.request_artist_enrichment(
            artist_evidence(name="Artist A", with_albums=True), generation=gen2
        )
        assert outcome_b.request is None
        assert outcome_b.resolution.status is IdentityResolutionStatus.NO_MATCH
        assert service.pending_count() == 0

        # Worker A comes back late: can neither commit nor leave a
        # zombie request.
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome_a.request, profile)
            is DeliveryVerdict.STALE
        )
        assert service.pending_count() == 0
        assert repository.write_count == 0


# ----------------------------------------------------------------------
# R1.3.1 invariants re-proven on the new begin semantics
# ----------------------------------------------------------------------


class TestBeginLinearizationRegression:
    def test_double_begin_regression(self):
        """R1.3.1 invariant (FIX-B) must hold with the new begin
        semantics: coordinator current token generation == Service
        current generation under two concurrent begins."""
        service = GatedBeginService(
            resolver=FakeIdentityResolver(),
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        coordinator = EnrichmentCoordinator(
            service=service,
            resolver=service._resolver,
            evidence_builder=LibraryEnrichmentEvidenceBuilder(_NoHintsExtractor()),
            mb_knowledge=_NoopKnowledge(),
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=ThreadPoolEnrichmentExecutor(max_workers=2),
            transport=None,
            enabled=lambda: True,
        )
        tokens = {}

        def begin(name):
            tokens[name] = coordinator._begin_operation(
                EnrichmentEntityKind.ARTIST, "artist a"
            )

        t1 = threading.Thread(target=begin, args=("t1",))
        t2 = threading.Thread(target=begin, args=("t2",))
        t1.start()
        assert service.gates[1]["entered"].wait(timeout=5)
        t2.start()
        if service.gates.get(2) is not None and service.gates[2]["entered"].wait(
            timeout=0.5
        ):
            service.gates[1]["proceed"].set()
            assert service.gates[1]["returned"].wait(timeout=5)
            service.gates[2]["proceed"].set()
            assert service.gates[2]["returned"].wait(timeout=5)
            service.gates[2]["post_alloc"].set()
            t2.join(timeout=5)
            assert not t2.is_alive()
            service.gates[1]["post_alloc"].set()
            t1.join(timeout=5)
            assert not t1.is_alive()
        else:
            service.gates[1]["proceed"].set()
            assert service.gates[1]["returned"].wait(timeout=5)
            service.gates[1]["post_alloc"].set()
            t1.join(timeout=5)
            assert not t1.is_alive()
            gate2 = None
            deadline = time.monotonic() + 5
            while gate2 is None and time.monotonic() < deadline:
                gate2 = service.gates.get(2)
            assert gate2 is not None, "caller #2 never reached begin_operation"
            assert gate2["entered"].wait(timeout=5)
            gate2["proceed"].set()
            assert gate2["returned"].wait(timeout=5)
            gate2["post_alloc"].set()
            t2.join(timeout=5)
            assert not t2.is_alive()

        key = (EnrichmentEntityKind.ARTIST, "artist a")
        service_current = service._operation_generations[key]
        coordinator_token = coordinator._operations[key]
        assert coordinator_token.generation == service_current
        generations = sorted(t.generation for t in tokens.values())
        assert generations[0] != generations[1]
        assert service_current == generations[1]


class TestOldFailureVsNewRequest:
    def test_old_failure_cannot_invalidate_new_request(self):
        """WHY THIS FAILED ON R1.3.1: worker A, woken with a transient
        error after B already registered its request, surfaced OFFLINE
        (obsolete error visible to the UI). B must commit exactly once."""
        harness = CoordinatorHarness(
            knowledge=GatedKnowledge(error=EnrichmentTransportError("offline"))
        )
        # SAME entity (key "artist a") for both operations; labels keep
        # the state buckets apart.
        harness.enrich_artist("Artist A", label="A")  # generation 1, blocked
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        # A registered its request and is parked in the provider fetch.
        assert harness.knowledge.entered_fetch.wait(timeout=5)

        # B begins (generation 2, SAME key) and completes normally.
        harness.enrich_artist("Artist A", label="B")
        assert harness.terminal["B"].wait(timeout=5)

        # A wakes with a transient error: obsolete -> CANCELLED, and its
        # exact request invalidation cannot touch B's request.
        harness.knowledge.release_fetch.set()
        assert harness.terminal["A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["A"][-1] is EnrichmentOperationState.CANCELLED
        assert EnrichmentOperationState.OFFLINE not in harness.states["A"]
        assert harness.states["B"][-1] is EnrichmentOperationState.READY
        # Exactly one commit: B's.
        assert harness.write_count == 1
        assert harness.service.pending_count() == 0
