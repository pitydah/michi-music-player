"""M6.9A-R3 — final foundation seal regressions.

Permanent behavioral gates for the R3 corrections:
- no-artist album auto-resolution is FORBIDDEN (even a unique title
  match); an explicit release-group hint remains usable
- release edition ids require corroboration
- identity READ failures are truthful (never "identity absent");
  presentation-safe knowledge reads degrade to None
- knowledge persistence failures yield STORAGE_FAILED (never COMMITTED)
- clear_identities / clear_knowledge are transactional (SQLite trigger
  failure injection — no monkeypatching internals)
- schema discovery is non-mutating and fail-closed (future / malformed /
  structurally corrupt databases are rejected without modification)
- historical V1 biography provenance is preserved
- corrupted content-addressed asset objects are detected and repaired
"""

import json
import sqlite3
from pathlib import Path

import pytest
from enrichment_fakes import (
    EnrichmentStorageError,
    FailingIdentityRepository,
    FailingKnowledgeRepository,
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
    IdentityResolutionStatus,
    ReleaseGroupCandidate,
    resolve_album_identity,
)
from michi.infrastructure.enrichment_assets import FilesystemEnrichmentAssetStore
from michi.infrastructure.enrichment_repository import (
    CURRENT_ENRICHMENT_SCHEMA,
    EnrichmentSchemaError,
    SqliteEnrichmentRepository,
)


def make_service(resolver=None, repository=None, identity_repository=None):
    return EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=repository or RecordingKnowledgeRepository(),
        identity_repository=identity_repository or InMemoryIdentityRepository(),
    )


class TestNoArtistAutoResolution:
    def test_unique_title_without_artist_is_ambiguous(self):
        """§29: a single title match (Daft Punk's Discovery) is NOT
        identity proof when the local album has no artist evidence."""
        resolution = resolve_album_identity(
            [
                ReleaseGroupCandidate(
                    release_group_id="rg-discovery",
                    title="Discovery",
                    artist_credit_names=("Daft Punk",),
                    first_release_year=2001,
                )
            ],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="Discovery",
                local_year=2001,
            ),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_title_year_without_artist_not_resolved(self):
        resolution = resolve_album_identity(
            [
                ReleaseGroupCandidate(
                    release_group_id="rg-a",
                    title="Discovery",
                    artist_credit_names=("Daft Punk",),
                    first_release_year=2001,
                )
            ],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="Discovery",
                local_year=2001,
            ),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_explicit_release_group_hint_still_usable(self):
        """§30: an explicit RG hint bypasses the search gate."""
        resolution = resolve_album_identity(
            [],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="Discovery",
                identity_hints=AlbumIdentityHints(release_group_ids=("rg-x",)),
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-x"

    def test_artist_name_evidence_restores_auto_resolution(self):
        resolution = resolve_album_identity(
            [
                ReleaseGroupCandidate(
                    release_group_id="rg-discovery",
                    title="Discovery",
                    artist_credit_names=("Daft Punk",),
                    first_release_year=2001,
                )
            ],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="Discovery",
                local_album_artist_name="Daft Punk",
                local_year=2001,
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-discovery"


class TestIdentityReadTruth:
    def test_artist_request_fails_closed_on_manual_read_failure(self):
        identity_repo = FailingIdentityRepository()
        identity_repo.fail_save = False
        identity_repo.fail_load = True
        resolver = FakeIdentityResolver(artists=[])
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
        )
        with pytest.raises(EnrichmentStorageError):
            service.request_artist_enrichment(evidence)
        assert len(resolver.artist_evidence) == 0
        assert service.pending_count() == 0

    def test_album_request_fails_closed_on_read_failure(self):
        identity_repo = FailingIdentityRepository()
        identity_repo.fail_save = False
        identity_repo.fail_load = True
        resolver = FakeIdentityResolver()
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
        )
        with pytest.raises(EnrichmentStorageError):
            service.request_album_enrichment(evidence)
        assert len(resolver.group_evidence) == 0
        assert service.pending_count() == 0

    def test_presentation_safe_knowledge_read(self):
        identity_repo = FailingIdentityRepository()
        identity_repo.fail_save = False
        identity_repo.fail_load = True
        service = make_service(identity_repository=identity_repo)
        # Presentation-facing helper degrades to None, never raises.
        assert service.get_artist_knowledge("artist a") is None
        assert service.get_album_knowledge("album-a") is None


class TestKnowledgePersistenceTruth:
    def test_artist_save_failure_is_storage_failed(self):
        knowledge = FailingKnowledgeRepository()
        knowledge.fail_save = True
        service = make_service(repository=knowledge)
        outcome = service.request_artist_enrichment(
            ArtistIdentityEvidence(
                local_artist_key="artist a",
                local_artist_name="Artist A",
                identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
            )
        )
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.STORAGE_FAILED
        )
        assert knowledge.load_artist_profile("artist a") is None
        # The request is terminal: a second delivery is UNKNOWN.
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.UNKNOWN
        )

    def test_album_save_failure_is_storage_failed(self):
        knowledge = FailingKnowledgeRepository()
        knowledge.fail_save = True
        service = make_service(repository=knowledge)
        outcome = service.request_album_enrichment(
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="Album X",
                identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
            )
        )
        profile = service._album_provider.fetch_profile("album-a", "rg-a")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.STORAGE_FAILED
        )
        assert knowledge.load_album_profile("album-a") is None

    def test_failure_handler_remains_zero_write(self):
        knowledge = RecordingKnowledgeRepository()
        service = make_service(repository=knowledge)
        outcome = service.request_artist_enrichment(
            ArtistIdentityEvidence(
                local_artist_key="artist a",
                local_artist_name="Artist A",
                identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
            )
        )
        assert (
            service.deliver_artist_failure(outcome.request) is DeliveryVerdict.COMMITTED
        )
        assert knowledge.write_count == 0


class TestTransactionalClears:
    def _repo_with_identity_rows(self, db_path: Path) -> SqliteEnrichmentRepository:
        repo = SqliteEnrichmentRepository(db_path)
        from michi.domain.enrichment import (
            AlbumExternalIdentity,
            ArtistExternalIdentity,
            MatchMethod,
        )

        repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="artist a",
                external_artist_id="mb-a",
                match_method=MatchMethod.MANUAL,
            )
        )
        repo.save_album_identity(
            AlbumExternalIdentity(local_album_key="album a", release_group_id="rg-a")
        )
        return repo

    def _install_fail_trigger(self, db_path: Path, table: str) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                f"CREATE TRIGGER fail_{table}_clear BEFORE DELETE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'injected clear failure'); END"
            )
            conn.commit()
        finally:
            conn.close()

    def test_clear_identities_rolls_back_atomically(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = self._repo_with_identity_rows(db_path)
        self._install_fail_trigger(db_path, "album_identity")
        with pytest.raises(EnrichmentStorageError):
            repo.clear_identities()
        # ROLLBACK: BOTH tables keep their rows.
        assert repo.load_artist_identity("artist a") is not None
        assert repo.load_album_identity("album a") is not None

    def test_clear_knowledge_rolls_back_atomically(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        from michi.domain.enrichment import ArtistKnowledgeProfile

        repo.save_artist_profile(
            ArtistKnowledgeProfile(
                local_artist_key="artist a", external_artist_id="mb-a"
            )
        )
        repo.save_album_profile(_album_profile())
        self._install_fail_trigger(db_path, "album_knowledge")
        with pytest.raises(EnrichmentStorageError):
            repo.clear_knowledge()
        assert repo.load_artist_profile("artist a") is not None
        assert repo.load_album_profile("album a") is not None


def _album_profile():
    from michi.domain.enrichment import AlbumKnowledgeProfile

    return AlbumKnowledgeProfile(local_album_key="album a", release_group_id="rg-a")


class TestSchemaFailClosed:
    @staticmethod
    def _make_meta_only_db(db_path: Path, version: str) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE enrichment_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", version),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _master_snapshot(db_path: Path) -> list:
        conn = sqlite3.connect(str(db_path))
        try:
            return conn.execute(
                "SELECT type, name FROM sqlite_master ORDER BY name"
            ).fetchall()
        finally:
            conn.close()

    def test_future_schema_rejected_without_mutation(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._make_meta_only_db(db_path, "99")
        before = self._master_snapshot(db_path)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert self._master_snapshot(db_path) == before

    @pytest.mark.parametrize("bad_version", ["banana", "", "-1", "0"])
    def test_malformed_version_rejected_without_mutation(self, tmp_path, bad_version):
        db_path = tmp_path / "enrichment.db"
        self._make_meta_only_db(db_path, bad_version)
        before = self._master_snapshot(db_path)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert self._master_snapshot(db_path) == before

    def test_current_schema_structural_corruption_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("DROP TABLE artist_identity")
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA


class TestHistoricalBiographyProvenance:
    def test_v1_biography_source_preserved(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        conn = sqlite3.connect(str(db_path))
        payload = {
            "local_artist_key": "the cure",
            "external_artist_id": "mb-cure",
            "biography": "English rock band.",
            "external_genres": ["Post-Punk"],
            "begin_year": 1976,
            "end_year": 0,
            "artwork_asset_id": "",
            "source": "legacy-source",
            "generation": 1,
        }
        try:
            conn.execute(
                "CREATE TABLE artist_knowledge ("
                "local_artist_key TEXT PRIMARY KEY,"
                "profile TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE album_knowledge ("
                "local_album_key TEXT PRIMARY KEY,"
                "profile TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE enrichment_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "1"),
            )
            conn.execute(
                "INSERT INTO artist_knowledge VALUES(?, ?)",
                ("the cure", json.dumps(payload)),
            )
            conn.commit()
        finally:
            conn.close()

        repo = SqliteEnrichmentRepository(db_path)
        profile = repo.load_artist_profile("the cure")
        assert profile is not None
        assert profile.provenance.provider == "legacy-source"
        assert profile.biography_provenance.provider == "legacy-source"
        # Unsupported provenance fields stay UNKNOWN — never invented.
        assert profile.biography_provenance.source_url == ""
        assert profile.biography_provenance.license == ""
        assert profile.biography_provenance.language == ""
        assert profile.biography_provenance.attribution == ""


class TestCorruptedContentObject:
    @staticmethod
    def _make_png(color: int) -> bytes:
        image = QImage(8, 6, QImage.Format_RGB32)
        image.fill(color)
        buffer = QBuffer()
        assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert image.save(buffer, "PNG")
        return bytes(buffer.data())

    def test_corrupted_existing_object_detected_and_repaired(self, tmp_path):
        from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind

        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        data = self._make_png(0x112233)
        record = EnrichmentAssetRecord(
            asset_id="cover-1",
            entity_kind=EnrichmentEntityKind.ARTIST,
            external_entity_id="mb-a",
            mime_type="image/png",
        )
        first = store.store(record, data)
        assert first is not None
        object_path = tmp_path / "assets" / first.managed_object
        assert object_path.is_file()
        # Corrupt the content without changing the filename.
        object_path.write_bytes(b"corrupted-bytes")

        second = store.store(record, data)
        assert second is not None
        assert second.checksum == first.checksum
        # The object was verified and rewritten atomically.
        assert object_path.read_bytes() == data
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == data
