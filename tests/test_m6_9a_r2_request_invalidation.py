"""M6.9A-R2 — request invalidation + identity transition contracts.

Behavioral gates (§19-26, §70-72, §100-101):
- reset during flight: late result STALE, ZERO writes, identity gone
- clear_identities during flight: every late result STALE, ZERO writes
- missing current identity blocks delivery (defense-in-depth)
- AUTO identity change invalidates old knowledge; EMBEDDED_HINT too
- same-id MatchMethod change preserves knowledge
- release-edition-only change invalidates release-level knowledge
- knowledge read authority: stale profiles are never presented
"""

from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
)


def make_service(resolver=None, album_provider=None):
    repository = RecordingKnowledgeRepository()
    identity_repository = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=album_provider or FakeAlbumProvider(),
        repository=repository,
        identity_repository=identity_repository,
    )
    return service, repository, identity_repository


def artist_evidence(name="Artist A", mbids=()):
    return ArtistIdentityEvidence(
        local_artist_key=name.casefold(),
        local_artist_name=name,
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


class TestResetDuringFlight:
    def test_reset_artist_stale_zero_writes(self):
        service, repository, identity_repo = make_service()
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        service.reset_artist_identity("artist a")
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        assert identity_repo.load_artist_identity("artist a") is None

    def test_reset_album_stale_zero_writes(self):
        service, repository, identity_repo = make_service()
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",))
        )
        service.reset_album_identity("album-a")
        profile = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        assert identity_repo.load_album_identity("album-a") is None


class TestClearIdentitiesDuringFlight:
    def test_clear_identities_stales_everything(self):
        service, repository, identity_repo = make_service()
        artist_outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        album_outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",))
        )
        service.clear_identities()
        artist_profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        album_profile = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_artist_profile(artist_outcome.request, artist_profile)
            is DeliveryVerdict.STALE
        )
        assert (
            service.deliver_album_profile(album_outcome.request, album_profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0
        assert identity_repo.load_artist_identity("artist a") is None
        assert identity_repo.load_album_identity("album-a") is None
        assert repository.artists == {} and repository.albums == {}


class TestMissingIdentityBlocksDelivery:
    def test_artist_delivery_without_current_identity_is_stale(self):
        service, repository, identity_repo = make_service()
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        # Simulate the identity authority losing the row OUTSIDE the
        # service (no ledger invalidation): delivery must still be STALE.
        identity_repo.delete_artist_identity("artist a")
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_album_delivery_without_current_identity_is_stale(self):
        service, repository, identity_repo = make_service()
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-a",))
        )
        identity_repo.delete_album_identity("album-a")
        profile = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0


class TestIdentityTransitionKnowledgeInvalidation:
    def test_auto_identity_change_invalidates_old_knowledge(self):
        """AUTO X + profile X -> resolver yields AUTO Y -> profile X
        deleted before Y becomes current."""
        resolver = FakeIdentityResolver(artists=[])
        service, repository, identity_repo = make_service(resolver=resolver)

        outcome_x = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-x",))
        )
        service.deliver_artist_profile(
            outcome_x.request,
            service._artist_provider.fetch_profile("artist a", "mb-x"),
        )
        assert repository.load_artist_profile("artist a") is not None

        outcome_y = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-y",))
        )
        assert outcome_y.request.external_entity_id == "mb-y"
        # Old knowledge invalidated by the transition.
        assert repository.load_artist_profile("artist a") is None
        # Old in-flight result can never commit.
        assert (
            service.deliver_artist_profile(
                outcome_x.request,
                service._artist_provider.fetch_profile("artist a", "mb-x"),
            )
            is DeliveryVerdict.STALE
        )
        assert (
            identity_repo.load_artist_identity("artist a").external_artist_id == "mb-y"
        )

    def test_embedded_hint_change_invalidates_old_knowledge(self):
        resolver = FakeIdentityResolver(artists=[])
        service, repository, _ = make_service(resolver=resolver)
        first = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-x",))
        )
        service.deliver_artist_profile(
            first.request, service._artist_provider.fetch_profile("artist a", "mb-x")
        )
        second = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-y",))
        )
        assert second.request.external_entity_id == "mb-y"
        assert repository.load_artist_profile("artist a") is None

    def test_same_id_method_change_preserves_knowledge(self):
        """§71: AUTO X -> MANUAL X: knowledge X remains."""
        resolver = FakeIdentityResolver(artists=[])
        service, repository, identity_repo = make_service(resolver=resolver)
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-x",))
        )
        service.deliver_artist_profile(
            outcome.request, service._artist_provider.fetch_profile("artist a", "mb-x")
        )
        service.confirm_artist_identity("artist a", "mb-x")
        identity = identity_repo.load_artist_identity("artist a")
        assert identity.match_method.name == "MANUAL"
        assert repository.load_artist_profile("artist a") is not None

    def test_release_edition_change_invalidates_old_knowledge(self):
        """§72: (rg-x, rel-A) -> (rg-x, rel-B): old release knowledge
        deleted; old in-flight rel-A result STALE; rel-B can commit."""
        service, repository, identity_repo = make_service()
        service.confirm_album_identity("album-a", "rg-x", release_id="rel-a")
        outcome_a = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-x",), release_ids=("rel-a",))
        )
        profile_a = service._album_provider.fetch_profile("album-a", "rg-x", "rel-a")
        assert (
            service.deliver_album_profile(outcome_a.request, profile_a)
            is DeliveryVerdict.COMMITTED
        )
        assert repository.load_album_profile("album-a") is not None

        # Edition change to rel-B (same release group).
        service.confirm_album_identity("album-a", "rg-x", release_id="rel-b")
        assert repository.load_album_profile("album-a") is None

        # Old rel-A response is STALE.
        assert (
            service.deliver_album_profile(outcome_a.request, profile_a)
            is DeliveryVerdict.STALE
        )
        # New rel-B response commits.
        outcome_b = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-x",), release_ids=("rel-b",))
        )
        profile_b = service._album_provider.fetch_profile("album-a", "rg-x", "rel-b")
        assert (
            service.deliver_album_profile(outcome_b.request, profile_b)
            is DeliveryVerdict.COMMITTED
        )
        assert identity_repo.load_album_identity("album-a").release_id == "rel-b"


class TestKnowledgeReadAuthority:
    def test_stale_artist_profile_never_presented(self):
        service, repository, _ = make_service()
        service.confirm_artist_identity("artist a", "mb-x")
        # A stale row exists in storage (external id != current identity):
        # the transition normally deletes it, but the READ authority must
        # ALSO hide it if such a row ever appears.
        repository.save_artist_profile(
            service._artist_provider.fetch_profile("artist a", "mb-old")
        )
        assert repository.load_artist_profile("artist a") is not None
        assert service.get_artist_knowledge("artist a") is None

    def test_missing_identity_hides_profile(self):
        service, repository, _ = make_service()
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-x",))
        )
        service.deliver_artist_profile(
            outcome.request, service._artist_provider.fetch_profile("artist a", "mb-x")
        )
        service.reset_artist_identity("artist a")
        assert repository.load_artist_profile("artist a") is None
        assert service.get_artist_knowledge("artist a") is None

    def test_album_knowledge_requires_group_and_edition_match(self):
        service, _, _ = make_service()
        service.confirm_album_identity("album-a", "rg-x", release_id="rel-a")
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-x",), release_ids=("rel-a",))
        )
        profile = service._album_provider.fetch_profile("album-a", "rg-x", "rel-a")
        service.deliver_album_profile(outcome.request, profile)
        assert service.get_album_knowledge("album-a") is not None
        service.confirm_album_identity("album-a", "rg-x", release_id="rel-b")
        assert service.get_album_knowledge("album-a") is None
