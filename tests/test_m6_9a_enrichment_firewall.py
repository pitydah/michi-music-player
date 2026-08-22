"""M6.9A — enrichment async-correlation firewall (service-level).

RED phase: fails at collection until ``michi/application/enrichment_service``
exists.

Coverage (required M6.9A concurrency tests):
- Artist A + Artist B, response B first then A: B data belongs only to B,
  A data only to A — no shared mutable active entity.
- A completes after A's local identity became stale: stale result discarded.
- Album A + Album B, reverse-order responses: ZERO cross-application.
- Two albums with similar names: ZERO cross-application.
- Ambiguous artists never receive biography/photo (no request, no write).
- Payload/request correlation mismatches are rejected (MISMATCHED).
- Failure delivery closes the pending request with ZERO repository writes.
"""

from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    RecordingAssetStore,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_service import (
    EnrichmentService,
)
from michi.domain.enrichment import (
    ArtistCandidate,
    DeliveryVerdict,
    ExternalIdentityHints,
    IdentityEvidence,
    IdentityResolutionStatus,
    ReleaseGroupCandidate,
)


def make_service(resolver=None, artist_provider=None, album_provider=None):
    service = EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=artist_provider or FakeArtistProvider(),
        album_provider=album_provider or FakeAlbumProvider(),
        repository=RecordingKnowledgeRepository(),
        asset_store=RecordingAssetStore(),
    )
    return service, service._repository


class TestArtistConcurrencyFirewall:
    def test_b_delivered_first_no_cross_application(self):
        service, repo = make_service(
            resolver=FakeIdentityResolver(artists=[])  # hint-driven below
        )
        evidence_a = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        evidence_b = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-b",))
        )
        outcome_a = service.request_artist_enrichment("artist-a", evidence_a)
        outcome_b = service.request_artist_enrichment("artist-b", evidence_b)
        assert outcome_a.request is not None and outcome_b.request is not None

        profile_b = service._artist_provider.fetch_profile("artist-b", "mb-b")
        profile_a = service._artist_provider.fetch_profile("artist-a", "mb-a")
        verdict_b = service.deliver_artist_profile(outcome_b.request, profile_b)
        verdict_a = service.deliver_artist_profile(outcome_a.request, profile_a)
        assert verdict_b is DeliveryVerdict.COMMITTED
        assert verdict_a is DeliveryVerdict.COMMITTED

        # Ownership: B data only under B, A data only under A.
        stored_b = repo.load_artist_profile("artist-b")
        stored_a = repo.load_artist_profile("artist-a")
        assert stored_b is not None and stored_b.external_artist_id == "mb-b"
        assert stored_a is not None and stored_a.external_artist_id == "mb-a"
        assert stored_b.biography != stored_a.biography

    def test_stale_identity_result_discarded(self):
        service, repo = make_service(resolver=FakeIdentityResolver(artists=[]))
        evidence_v1 = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-old",))
        )
        outcome_v1 = service.request_artist_enrichment(
            "artist-a", evidence_v1, generation=1
        )
        # Local identity refreshed: the same ArtistRef now resolves elsewhere.
        evidence_v2 = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-new",))
        )
        outcome_v2 = service.request_artist_enrichment(
            "artist-a", evidence_v2, generation=2
        )

        stale_profile = service._artist_provider.fetch_profile("artist-a", "mb-old")
        verdict_stale = service.deliver_artist_profile(
            outcome_v1.request, stale_profile
        )
        assert verdict_stale is DeliveryVerdict.STALE

        fresh_profile = service._artist_provider.fetch_profile("artist-a", "mb-new")
        verdict_fresh = service.deliver_artist_profile(
            outcome_v2.request, fresh_profile
        )
        assert verdict_fresh is DeliveryVerdict.COMMITTED
        stored = repo.load_artist_profile("artist-a")
        assert stored is not None and stored.external_artist_id == "mb-new"
        assert repo.artist_saves == [fresh_profile]

    def test_no_mutable_active_entity_field(self):
        service, _ = make_service()
        for name in (
            "_active_artist",
            "_active_album",
            "_active_key",
            "_current_artist",
            "_current_album",
            "_current_entity",
        ):
            assert not hasattr(service, name)


class TestAlbumConcurrencyFirewall:
    def test_album_reverse_order_zero_cross_application(self):
        service, repo = make_service(
            resolver=FakeIdentityResolver(groups=[]),
        )
        evidence_a = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-a")
        )
        evidence_b = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-b")
        )
        outcome_a = service.request_album_enrichment("album-a", evidence_a)
        outcome_b = service.request_album_enrichment("album-b", evidence_b)
        assert outcome_a.request is not None and outcome_b.request is not None

        profile_b = service._album_provider.fetch_profile("album-b", "rg-b")
        profile_a = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_album_profile(outcome_b.request, profile_b)
            is DeliveryVerdict.COMMITTED
        )
        assert (
            service.deliver_album_profile(outcome_a.request, profile_a)
            is DeliveryVerdict.COMMITTED
        )

        stored_a = repo.load_album_profile("album-a")
        stored_b = repo.load_album_profile("album-b")
        assert stored_a is not None and stored_a.release_group_id == "rg-a"
        assert stored_b is not None and stored_b.release_group_id == "rg-b"

    def test_similar_album_names_zero_cross_application(self):
        resolver = FakeIdentityResolver(
            groups=[
                ReleaseGroupCandidate(release_group_id="rg-a", title="Greatest Hits"),
                ReleaseGroupCandidate(release_group_id="rg-b", title="Greatest Hits"),
            ]
        )
        service, repo = make_service(resolver=resolver)
        # Two DIFFERENT local albums (same title, different local keys
        # because resolved album artists differ) with explicit hints.
        evidence_a = IdentityEvidence(
            local_album_titles=("Greatest Hits",),
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-a"),
        )
        evidence_b = IdentityEvidence(
            local_album_titles=("Greatest Hits",),
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-b"),
        )
        outcome_a = service.request_album_enrichment("album-key-a", evidence_a)
        outcome_b = service.request_album_enrichment("album-key-b", evidence_b)
        assert outcome_a.request is not None
        assert outcome_b.request is not None

        profile_a = service._album_provider.fetch_profile("album-key-a", "rg-a")
        profile_b = service._album_provider.fetch_profile("album-key-b", "rg-b")
        service.deliver_album_profile(outcome_a.request, profile_a)
        service.deliver_album_profile(outcome_b.request, profile_b)

        stored_a = repo.load_album_profile("album-key-a")
        stored_b = repo.load_album_profile("album-key-b")
        assert stored_a.release_group_id == "rg-a"
        assert stored_b.release_group_id == "rg-b"


class TestCorrelationMismatchGuard:
    def test_payload_from_other_artist_rejected(self):
        service, repo = make_service(resolver=FakeIdentityResolver(artists=[]))
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        outcome = service.request_artist_enrichment("artist-a", evidence)
        wrong = service._artist_provider.fetch_profile("artist-a", "mb-b")
        verdict = service.deliver_artist_profile(outcome.request, wrong)
        assert verdict is DeliveryVerdict.MISMATCHED
        assert repo.write_count == 0

    def test_album_request_delivered_as_artist_rejected(self):
        service, repo = make_service(resolver=FakeIdentityResolver(artists=[]))
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        outcome = service.request_artist_enrichment("artist-a", evidence)
        profile = service._artist_provider.fetch_profile("artist-a", "mb-a")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.MISMATCHED
        )
        assert repo.write_count == 0


class TestAmbiguousNeverEnriches:
    def test_ambiguous_artist_gets_no_request_and_no_profile(self):
        service, repo = make_service(resolver=FakeIdentityResolver(artists=[]))
        # No hints, no evidence: name alone can never resolve.
        outcome = service.request_artist_enrichment("john williams", IdentityEvidence())
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert repo.write_count == 0

    def test_ambiguous_artist_never_receives_biography_or_photo(self):
        service, repo = make_service(
            resolver=FakeIdentityResolver(
                artists=[ArtistCandidate("mb-a"), ArtistCandidate("mb-b")]
            ),
            artist_provider=FakeArtistProvider(),
        )
        evidence = IdentityEvidence(local_album_titles=("Same Title",))
        outcome = service.request_artist_enrichment("artist-a", evidence)
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert repo.write_count == 0
        assert repo.artists == {}


class TestFailureLeavesNothing:
    def test_artist_failure_closes_request_with_zero_writes(self):
        service, repo = make_service(resolver=FakeIdentityResolver(artists=[]))
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        outcome = service.request_artist_enrichment("artist-a", evidence)
        assert (
            service.deliver_artist_failure(outcome.request) is DeliveryVerdict.COMMITTED
        )
        assert repo.write_count == 0
        assert service.pending_count() == 0

    def test_offline_provider_never_writes(self):
        service, repo = make_service(
            resolver=FakeIdentityResolver(artists=[]),
            artist_provider=FakeArtistProvider(offline=True),
        )
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        outcome = service.request_artist_enrichment("artist-a", evidence)
        from michi.application.enrichment_ports import EnrichmentProviderError

        try:
            service._artist_provider.fetch_profile("artist-a", "mb-a")
            raised = False
        except EnrichmentProviderError:
            raised = True
        assert raised
        service.deliver_artist_failure(outcome.request)
        assert repo.write_count == 0
        assert repo.artists == {}
