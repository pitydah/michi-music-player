"""M6.9A-R1 — persistent identity authority tests (real SQLite temp DBs).

Coverage:
- identity != knowledge: artist/album identity rows stored independently
- schema 2 + transactional migration 1 -> 2 preserving knowledge profiles
- clear_knowledge() preserves MANUAL identity mappings
- reset_*_identity removes mapping AND associated knowledge
- MANUAL identity overrides automatic re-resolution
- identity CHANGE invalidates the old knowledge profile
- match_method provenance: EMBEDDED_HINT / AUTO / MANUAL
- read validation: mismatched/malformed rows are skipped
- failure delivery kind guards never consume the wrong entity
"""

import sqlite3

import pytest
from enrichment_fakes import (
    FailingIdentityRepository,
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistExternalIdentity,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
    IdentityStatus,
    MatchMethod,
)
from michi.infrastructure.enrichment_repository import (
    CURRENT_ENRICHMENT_SCHEMA,
    EnrichmentSchemaError,
    SqliteEnrichmentRepository,
)


def make_service(resolver=None, artist_provider=None, album_provider=None):
    repository = RecordingKnowledgeRepository()
    identity_repository = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=artist_provider or FakeArtistProvider(),
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


class TestIdentityPersistence:
    def test_artist_identity_round_trip(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        identity = ArtistExternalIdentity(
            local_artist_key="the cure",
            external_artist_id="mb-xyz",
            match_method=MatchMethod.MANUAL,
            resolved_at="2026-08-22T00:00:00+00:00",
        )
        repo.save_artist_identity(identity)
        loaded = repo.load_artist_identity("the cure")
        assert loaded == identity
        assert loaded is not None and loaded.status is IdentityStatus.RESOLVED

    def test_album_identity_round_trip(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        identity = AlbumExternalIdentity(
            local_album_key="album-key",
            release_group_id="rg-1",
            release_id="",
            match_method=MatchMethod.AUTO,
        )
        repo.save_album_identity(identity)
        loaded = repo.load_album_identity("album-key")
        assert loaded == identity
        assert loaded is not None and loaded.release_id == ""

    def test_identity_independent_of_knowledge(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        repo.save_artist_identity(
            ArtistExternalIdentity(local_artist_key="k", external_artist_id="mb-1")
        )
        repo.clear_knowledge()
        assert repo.load_artist_identity("k") is not None
        repo.clear_identities()
        assert repo.load_artist_identity("k") is None

    def test_malformed_identity_row_raises(self, tmp_path):
        """R3.1: malformed identity authority is CORRUPTION — it raises,
        never silently degrades to 'no identity exists'."""
        from michi.application.enrichment_ports import EnrichmentStorageError

        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?)",
                ("bad-key", "mb-x", "NOT_A_STATUS", "NOT_A_METHOD", "when"),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("bad-key")
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identities()


class TestSchemaMigration:
    """R2: the realistic migration chain (literal V1/V2 fixtures, real
    data transformation) is covered by tests/test_m6_9a_r2_migrations.py.
    Here: schema version + fail-closed behavior only."""

    def test_fresh_database_is_current_schema(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

    def test_newer_schema_fails_closed(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE enrichment_meta SET value = '99' "
                "WHERE key = 'enrichment_schema_version'"
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)


class TestManualIdentityAuthority:
    def test_manual_overrides_auto_rematch(self):
        resolver = FakeIdentityResolver(artists=[])
        service, _, identity_repo = make_service(resolver=resolver)
        # Automatic resolution would go to mb-auto; the user picks mb-manual.
        service.confirm_artist_identity("artist a", "mb-manual")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-auto",))
        )
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-manual"
        identity = identity_repo.load_artist_identity("artist a")
        assert identity is not None
        assert identity.match_method is MatchMethod.MANUAL

    def test_reset_permits_rematching(self):
        service, _, identity_repo = make_service()
        service.confirm_artist_identity("artist a", "mb-manual")
        service.reset_artist_identity("artist a")
        assert identity_repo.load_artist_identity("artist a") is None
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-auto",))
        )
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-auto"

    def test_identity_change_invalidates_old_knowledge(self):
        service, repository, identity_repo = make_service()
        service.confirm_artist_identity("artist a", "mb-a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        assert repository.load_artist_profile("artist a") is not None
        # Identity changes to a different MBID: knowledge must vanish.
        service.confirm_artist_identity("artist a", "mb-b")
        assert repository.load_artist_profile("artist a") is None
        assert (
            identity_repo.load_artist_identity("artist a").external_artist_id == "mb-b"
        )

    def test_reset_clears_identity_and_knowledge(self):
        service, repository, identity_repo = make_service()
        service.confirm_artist_identity("artist a", "mb-a")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        service.deliver_artist_profile(outcome.request, profile)
        service.reset_artist_identity("artist a")
        assert identity_repo.load_artist_identity("artist a") is None
        assert repository.load_artist_profile("artist a") is None

    def test_clear_knowledge_preserves_manual_identities(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        identity_repo = SqliteEnrichmentRepository(db_path)
        service = EnrichmentService(
            resolver=FakeIdentityResolver(),
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=repo,
            identity_repository=identity_repo,
        )
        service.confirm_artist_identity("artist a", "mb-manual")
        service.confirm_album_identity("album a", "rg-manual")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-manual",))
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-manual")
        service.deliver_artist_profile(outcome.request, profile)
        assert repo.load_artist_profile("artist a") is not None

        service.clear_knowledge()
        assert repo.load_artist_profile("artist a") is None
        assert identity_repo.load_artist_identity("artist a") is not None
        assert identity_repo.load_album_identity("album a") is not None

    def test_clear_identities_clears_mappings_and_knowledge(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        identity_repo = SqliteEnrichmentRepository(db_path)
        service = EnrichmentService(
            resolver=FakeIdentityResolver(),
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=repo,
            identity_repository=identity_repo,
        )
        service.confirm_artist_identity("artist a", "mb-manual")
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-manual",))
        )
        service.deliver_artist_profile(
            outcome.request,
            service._artist_provider.fetch_profile("artist a", "mb-manual"),
        )
        # R2 contract: clear_identities = invalidate requests + clear
        # identity authority + clear active knowledge (no orphan rows).
        service.clear_identities()
        assert identity_repo.load_artist_identity("artist a") is None
        assert repo.load_artist_profile("artist a") is None


class TestMatchMethodProvenance:
    def test_embedded_hint_method_persisted(self):
        service, _, identity_repo = make_service()
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        assert outcome.request is not None
        identity = identity_repo.load_artist_identity("artist a")
        assert identity is not None
        assert identity.match_method is MatchMethod.EMBEDDED_HINT

    def test_auto_method_persisted(self):
        from michi.domain.enrichment import ArtistCandidate, LocalAlbumEvidence

        resolver = FakeIdentityResolver(
            artists=[
                ArtistCandidate(
                    "mb-a",
                    canonical_name="Artist A",
                    known_albums=(LocalAlbumEvidence("Album One", 1980),),
                )
            ]
        )
        service, _, identity_repo = make_service(resolver=resolver)
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            known_albums=(LocalAlbumEvidence("Album One", 1980),),
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is not None
        identity = identity_repo.load_artist_identity("artist a")
        assert identity is not None
        assert identity.match_method is MatchMethod.AUTO


class TestFailureKindGuards:
    """R1 §39-40: wrong failure handler must NOT consume the request."""

    def test_deliver_artist_failure_rejects_album_request(self):
        from michi.domain.enrichment import (
            AlbumIdentityEvidence,
            AlbumIdentityHints,
        )

        service, _, _ = make_service()
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
        )
        album_outcome = service.request_album_enrichment(evidence)
        assert album_outcome.request is not None
        assert (
            service.deliver_artist_failure(album_outcome.request)
            is DeliveryVerdict.MISMATCHED
        )
        # The album request is still pending: correct delivery succeeds.
        profile = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_album_profile(album_outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )

    def test_deliver_album_failure_rejects_artist_request(self):
        service, _, _ = make_service()
        artist_outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        assert artist_outcome.request is not None
        assert (
            service.deliver_album_failure(artist_outcome.request)
            is DeliveryVerdict.MISMATCHED
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(artist_outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )


class TestDeliveryIdentityGuard:
    def test_delivery_after_identity_change_is_stale(self):
        service, repository, _ = make_service()
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        # Identity changes while the request is in flight.
        service.confirm_artist_identity("artist a", "mb-b")
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )
        assert repository.write_count == 0

    def test_superseded_request_stale_then_committed(self):
        from michi.domain.enrichment import EnrichmentEntityKind

        service, repository, _ = make_service()
        service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a", 1)
        first = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=1
        )
        service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a", 2)
        second = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",)), generation=2
        )
        assert (
            service.deliver_artist_profile(
                first.request,
                service._artist_provider.fetch_profile("artist a", "mb-a"),
            )
            is DeliveryVerdict.STALE
        )
        assert (
            service.deliver_artist_profile(
                second.request,
                service._artist_provider.fetch_profile("artist a", "mb-a"),
            )
            is DeliveryVerdict.COMMITTED
        )
        assert repository.write_count == 1


class TestStorageFailureTruth:
    """R2 §35-41: identity persistence must never fail silently."""

    def _service_with(self, identity_repo):
        return EnrichmentService(
            resolver=FakeIdentityResolver(),
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=RecordingKnowledgeRepository(),
            identity_repository=identity_repo,
        )

    def test_identity_save_failure_blocks_artist_request(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        service = self._service_with(identity_repo)
        with pytest.raises(EnrichmentStorageError):
            service.request_artist_enrichment(
                artist_evidence(name="Artist A", mbids=("mb-a",))
            )
        assert service.pending_count() == 0
        assert identity_repo.load_artist_identity("artist a") is None

    def test_identity_save_failure_blocks_album_request(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        service = self._service_with(identity_repo)
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
        )
        with pytest.raises(EnrichmentStorageError):
            service.request_album_enrichment(evidence)
        assert service.pending_count() == 0

    def test_manual_save_failure_is_truthful(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        service = self._service_with(identity_repo)
        with pytest.raises(EnrichmentStorageError):
            service.confirm_artist_identity("artist a", "mb-manual")
        assert identity_repo.load_artist_identity("artist a") is None

    def test_manual_album_save_failure_is_truthful(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        service = self._service_with(identity_repo)
        with pytest.raises(EnrichmentStorageError):
            service.confirm_album_identity("album a", "rg-manual")

    def test_reset_delete_failure_invalidates_request_first(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        identity_repo.fail_save = False
        identity_repo.fail_delete = True
        service = self._service_with(identity_repo)
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", mbids=("mb-a",))
        )
        assert outcome.request is not None
        with pytest.raises(EnrichmentStorageError):
            service.reset_artist_identity("artist a")
        # Runtime safety: the pending request was invalidated BEFORE the
        # failing delete — the old result can never commit.
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STALE
        )

    def test_clear_identities_failure_is_truthful(self):
        from michi.application.enrichment_ports import EnrichmentStorageError

        identity_repo = FailingIdentityRepository()
        identity_repo.fail_save = False
        identity_repo.fail_delete = False
        identity_repo.fail_clear = True
        service = self._service_with(identity_repo)
        with pytest.raises(EnrichmentStorageError):
            service.clear_identities()
