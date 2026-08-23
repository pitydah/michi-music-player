"""M6.9-BACKEND-R1.3.1 — Final Begin Linearization + Album Dependency
Precommit Seal.

Deterministic interleavings ONLY (threading.Event, 2 real threads where
races are involved, ZERO sleeps; timeouts are safety bounds). Every
regression test documents the exact interleaving that broke R1.3 and
asserts a public-surface invariant; white-box reads are limited to the
explicitly authorized linearization observations (coordinator token /
service generation).

Seal matrix (§16):
  A  album resolving with Artist=A, Artist A->B before identity commit
  B  album resolving with Artist=A, Artist reset before identity commit
  C  artist-dependency knowledge delivery guard (kept from R1.3)
  D  two concurrent begin same entity -> token == Service current gen
  E  old begin can never publish over newer begin
  F  public cancel retires exactly the current generation
  G  manual confirm cancels the physical old token (barrier still rules)
  H  reset cancels the physical old token (barrier still rules)
  I  old failure cannot invalidate new request (kept from R1.3)
  J  cancel_all snapshot semantics (kept from R1.3)
  K  shutdown admission barrier (kept from R1.3)
  L  double delivery commits at most once (kept from R1.3)
  M  MANUAL never downgraded (kept from R1.3)
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
    ArtistKnowledgeProfile,
    EnrichmentEntityKind,
    IdentityResolutionStatus,
    KnowledgeProvenance,
    LocalAlbumEvidence,
    MatchMethod,
    ReleaseGroupCandidate,
)

# ----------------------------------------------------------------------
# shared evidence helpers
# ----------------------------------------------------------------------


def album_evidence_with_artist(key="album-a", artist_key="artist a"):
    """Album evidence WITHOUT release hints: resolution must go through
    the resolver (find_release_group_candidates), which the P0 tests
    block mid-flight. The artist key + name ride the evidence so the
    service derives the dependency from the persisted artist identity."""
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title="Album X",
        local_album_artist_key=artist_key,
        local_album_artist_name="Artist A",
        local_year=1980,
        identity_hints=AlbumIdentityHints(),
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
# P0 — Album artist dependency must be validated BEFORE the Album
# identity commit (FIX-A)
# ----------------------------------------------------------------------


class BlockingGroupResolver(ExternalIdentityResolverPort):
    """Blocks the FIRST release-group resolution on an Event; afterwards
    returns a perfectly valid release-group candidate that WOULD have
    been accepted using the original artist identity."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.group_calls = 0

    def find_release_group_candidates(self, evidence):
        self.group_calls += 1
        if self.group_calls == 1:
            self.entered.set()
            self.release.wait(timeout=15)
        return (
            ReleaseGroupCandidate(
                release_group_id="rg-x",
                title=evidence.local_album_title,
                artist_credit_external_ids=("mb-a",),
                artist_credit_names=(evidence.local_album_artist_name,),
                first_release_year=evidence.local_year,
            ),
        )

    def find_release_edition_candidates(self, evidence):
        return ()

    def find_artist_candidates(self, evidence):
        return ()


class TestAlbumDependencyPrecommit:
    """FIX-A: if an album resolution depended on a persisted Artist
    identity, that dependency must still hold at the EXACT moment the
    Album identity is persisted — not only at knowledge delivery."""

    def _begin_blocked_album(self, service):
        gen = service.begin_operation(EnrichmentEntityKind.ALBUM, "album-a")
        outcome = {}

        def work():
            outcome["result"] = service.request_album_enrichment(
                album_evidence_with_artist(), generation=gen
            )

        thread = threading.Thread(target=work)
        thread.start()
        return gen, outcome, thread

    def test_artist_a_to_b_while_album_resolution_blocked(self):
        """WHY THIS FAILED ON R1.3: request_album_enrichment read the
        Artist identity A, resolved the album with it, then re-entered
        the authority lock — where the ALBUM generation was still
        current — and persisted AlbumExternalIdentity BEFORE the artist
        change was visible. The dependency was only revalidated at
        knowledge delivery (protecting knowledge, NOT identity)."""
        service, repository, identity_repo = make_service(
            resolver=BlockingGroupResolver()
        )
        service.confirm_artist_identity("artist a", "mb-a")
        gen, outcome, thread = self._begin_blocked_album(service)
        assert service._resolver.entered.wait(timeout=5)  # mid-resolution

        # Artist A -> B while the album resolution is IN FLIGHT.
        service.confirm_artist_identity("artist a", "mb-b")
        service._resolver.release.set()
        thread.join(timeout=5)
        assert not thread.is_alive()

        result = outcome["result"]
        assert result.request is None
        assert result.resolution.status is IdentityResolutionStatus.SUPERSEDED
        assert identity_repo.load_album_identity("album-a") is None
        assert repository.write_count == 0
        assert service.pending_count() == 0

    def test_artist_reset_while_album_resolution_blocked(self):
        """WHY THIS FAILED ON R1.3: a reset deleted the artist identity
        while the album resolution was in flight, but the album gate
        never consulted it — the album identity built on the deleted
        artist was still persisted."""
        service, repository, identity_repo = make_service(
            resolver=BlockingGroupResolver()
        )
        service.confirm_artist_identity("artist a", "mb-a")
        gen, outcome, thread = self._begin_blocked_album(service)
        assert service._resolver.entered.wait(timeout=5)

        service.reset_artist_identity("artist a")
        service._resolver.release.set()
        thread.join(timeout=5)
        assert not thread.is_alive()

        result = outcome["result"]
        assert result.request is None
        assert result.resolution.status is IdentityResolutionStatus.SUPERSEDED
        assert identity_repo.load_album_identity("album-a") is None
        assert repository.write_count == 0
        assert service.pending_count() == 0

    def test_artist_unchanged_album_identity_commits(self):
        """CONTROL: with the dependency still valid at precommit time,
        the identity persists, the request registers and carries the
        captured dependency A; delivery then commits exactly once."""
        service, repository, identity_repo = make_service(
            resolver=BlockingGroupResolver()
        )
        service.confirm_artist_identity("artist a", "mb-a")
        gen, outcome, thread = self._begin_blocked_album(service)
        assert service._resolver.entered.wait(timeout=5)
        service._resolver.release.set()
        thread.join(timeout=5)
        assert not thread.is_alive()

        result = outcome["result"]
        assert result.request is not None
        assert result.resolution.status is IdentityResolutionStatus.RESOLVED
        assert result.request.artist_dependency_local_key == "artist a"
        assert result.request.artist_dependency_id == "mb-a"
        identity = identity_repo.load_album_identity("album-a")
        assert identity is not None and identity.release_group_id == "rg-x"
        assert service.pending_count() == 1

        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            service.deliver_album_profile(result.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1
        assert service.pending_count() == 0


# ----------------------------------------------------------------------
# P1 — _begin_operation must be linearizable (FIX-B)
# ----------------------------------------------------------------------


class GatedBeginService(EnrichmentService):
    """Gates EACH begin_operation call with per-call events so the test
    can force the R1.3 publication race: caller #1 obtains its
    generation but is held BEFORE returning, letting caller #2 obtain a
    NEWER generation and publish first — then caller #1 publishes its
    STALE token over the newer one."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gate_lock = threading.Lock()
        self._calls = 0
        self.gates: dict[int, dict[str, threading.Event]] = {}

    def begin_operation(self, entity_kind, local_entity_key):
        with self._gate_lock:
            self._calls += 1
            number = self._calls
            gate = {
                "entered": threading.Event(),
                "proceed": threading.Event(),
                "returned": threading.Event(),
                "post_alloc": threading.Event(),
            }
            self.gates[number] = gate
        gate = self.gates[number]
        gate["entered"].set()
        assert gate["proceed"].wait(timeout=15)
        generation = super().begin_operation(entity_kind, local_entity_key)
        gate["returned"].set()
        assert gate["post_alloc"].wait(timeout=15)
        return generation


class TestBeginLinearization:
    """FIX-B: admission + generation allocation + token creation +
    publication must be ONE linearization point."""

    def _concurrent_begins(self):
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
            # R1.3-style race window available. Drive the exact broken
            # interleaving: caller #1 allocates gen1 FIRST but publishes
            # LAST — caller #2 allocates gen2 and publishes, then caller
            # #1 publishes its STALE gen1 token over the newer one.
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
            # Linearizable coordinator: caller #2 could only enter AFTER
            # caller #1 fully published (single linearization point).
            service.gates[1]["proceed"].set()
            assert service.gates[1]["returned"].wait(timeout=5)
            service.gates[1]["post_alloc"].set()
            t1.join(timeout=5)
            assert not t1.is_alive()
            # Caller #2 was parked on the coordinator lock; its gate is
            # created when it reaches the service. Wait deterministically
            # for it (poll with deadline, no sleep) — a bare dict access
            # here races the worker's scheduling.
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
        return service, coordinator, tokens

    def test_two_concurrent_begins_same_key_linearize(self):
        """WHY THIS FAILED ON R1.3: _begin_operation published the token
        in a SECOND lock section after releasing the coordinator lock
        around service.begin_operation — T1 could obtain generation 1,
        T2 generation 2, and T1 could then publish its gen-1 token AFTER
        T2 published gen-2, leaving Coordinator token=gen1 while the
        Service current generation was gen2."""
        service, coordinator, tokens = self._concurrent_begins()
        key = (EnrichmentEntityKind.ARTIST, "artist a")

        generations = sorted(t.generation for t in tokens.values())
        assert generations[0] != generations[1]  # distinct generations
        service_current = service._operation_generations[key]
        coordinator_token = coordinator._operations[key]
        # THE invariant: coordinator token == service current generation
        # == the LAST linearization point (max generation stays current).
        assert coordinator_token.generation == service_current
        assert service_current == generations[1]

    def test_stale_begin_cannot_publish_over_newer_and_cancel_exact(self):
        """WHY THIS FAILED ON R1.3: the losing thread (gen-1 token)
        overwrote the winning token in the coordinator registry, so
        cancel_artist(key) retired generation 1 — while the SERVICE
        current generation was 2 — leaving generation 2 live with a
        dead coordinator token."""
        service, coordinator, tokens = self._concurrent_begins()
        key = (EnrichmentEntityKind.ARTIST, "artist a")
        generations = sorted(t.generation for t in tokens.values())
        winner_gen = service._operation_generations[key]
        loser_gen = generations[0] if generations[1] == winner_gen else generations[1]

        coordinator.cancel_artist("artist a")
        # Public cancel retires EXACTLY the coordinator-current token.
        assert not service.is_current_operation(
            EnrichmentEntityKind.ARTIST, "artist a", winner_gen
        )
        # The loser generation can never retire the (already retired)
        # current authority nor resurrect itself.
        assert (
            service.retire_operation(EnrichmentEntityKind.ARTIST, "artist a", loser_gen)
            is False
        )
        assert service._operation_generations[key] != loser_gen


# ----------------------------------------------------------------------
# P1 — manual / reset must cancel the physical old token (FIX-C)
# ----------------------------------------------------------------------


class GateResolver(ExternalIdentityResolverPort):
    """Blocks the first ``block_count`` resolver calls (artist AND
    release-group paths share the gate); afterwards returns resolvable
    candidates."""

    def __init__(self, block_count=1):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self._block_count = block_count

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
        return None


class _GatedKnowledge(_NoopKnowledge):
    """Blocks fetch_artist so the worker is deterministically parked
    AFTER registering its request (registration precedes the fetch)."""

    def __init__(self):
        self.entered_fetch = threading.Event()
        self.release_fetch = threading.Event()

    def fetch_artist(self, local_artist_key, external_artist_id):
        self.entered_fetch.set()
        self.release_fetch.wait(timeout=15)
        return super().fetch_artist(local_artist_key, external_artist_id)


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
    def __init__(self, knowledge=None, resolver_block_count=1):
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

    def enrich_artist(self, name):
        self.terminal.setdefault(name, threading.Event())
        artists, albums, tracks = _single_artist_model(name)

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

        self.coordinator.enrich_artist(artists[0], albums, tracks, on_state)

    def enrich_album(self, name):
        artists, albums, tracks = _single_artist_model(name)
        self.terminal.setdefault(name, threading.Event())

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

        self.coordinator.enrich_album(albums[0], on_state=on_state)

    @property
    def write_count(self) -> int:
        return self.repository.write_count

    def current_token(self, entity_kind, local_key):
        return self.coordinator._operations.get((entity_kind, local_key))


class TestManualResetCancelsPhysicalToken:
    """FIX-C: the coordinator marks the in-flight token CANCELLED when a
    manual confirm / reset runs — lifecycle truth — while the Service
    barrier remains the correctness authority."""

    def test_manual_confirm_cancels_artist_token(self):
        """WHY THIS FAILED ON R1.3: the coordinator passthrough confirmed
        the identity WITHOUT cancelling the in-flight token — the old
        worker stayed physically alive (provider calls, useless terminal
        states) even though the service gate blocked its writes."""
        harness = CoordinatorHarness()
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.confirm_artist_identity("artist a", "mb-manual")
        token = harness.current_token(EnrichmentEntityKind.ARTIST, "artist a")
        assert token is not None and token.cancelled is True
        harness.resolver.release.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL

    def test_reset_cancels_artist_token(self):
        """WHY THIS FAILED ON R1.3: same passthrough gap for reset — the
        old token was left running after the reset barrier."""
        harness = CoordinatorHarness()
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.reset_artist_identity("artist a")
        token = harness.current_token(EnrichmentEntityKind.ARTIST, "artist a")
        assert token is not None and token.cancelled is True
        harness.resolver.release.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        assert harness.identity_repo.load_artist_identity("artist a") is None

    def test_manual_confirm_cancels_album_token(self):
        """WHY THIS FAILED ON R1.3: the album passthrough had the same
        lifecycle gap — the in-flight album worker was not cancelled."""
        harness = CoordinatorHarness()
        harness.enrich_album("Album A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.coordinator.confirm_album_identity(
            "album-x", "rg-manual", release_id="rel-m"
        )
        token = harness.current_token(EnrichmentEntityKind.ALBUM, "album-x")
        assert token is not None and token.cancelled is True
        harness.resolver.release.set()
        assert harness.terminal["Album A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Album A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        identity = harness.identity_repo.load_album_identity("album-x")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL


class TestStaleTerminalConvergence:
    def test_stale_delivery_converges_to_cancelled_not_failed(self):
        """WHY THIS FAILED ON R1.3: _commit_* mapped ANY non-COMMITTED
        verdict to FAILED — an operation whose generation lost authority
        (STALE) surfaced as a user-facing functional error instead of
        converging to CANCELLED."""
        harness = CoordinatorHarness(knowledge=_GatedKnowledge())
        harness.enrich_artist("Artist A")
        assert harness.resolver.entered.wait(timeout=5)
        harness.resolver.release.set()
        # The worker registered its request and is parked in fetch.
        assert harness.knowledge.entered_fetch.wait(timeout=5)
        harness.service.confirm_artist_identity("artist a", "mb-manual")
        harness.knowledge.release_fetch.set()
        assert harness.terminal["Artist A"].wait(timeout=5)
        harness.coordinator._executor.shutdown(wait=True)

        assert harness.states["Artist A"][-1] is EnrichmentOperationState.CANCELLED
        assert harness.write_count == 0
        identity = harness.identity_repo.load_artist_identity("artist a")
        assert identity is not None and identity.match_method is MatchMethod.MANUAL
