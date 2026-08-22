"""M6.9A-R3.1 — final identity invariants + external asset safety.

Permanent behavioral gates for the last foundation corrections:
- persistent identity records are RESOLVED-only (impossible states raise)
- duplicate identical same-role hints are normalized (never conflicts)
- match authority precedence MANUAL > EMBEDDED_HINT > AUTO
- AUTO identities are revoked when fresh evidence no longer supports them
- malformed identity authority rows raise (never "no identity exists")
- V1/V2/V3 migration shapes are fail-closed (partial V2 rejected,
  mislabeled V2-as-V3 rejected)
- version() is truthful (never a fake 0)
- external images are byte-, dimension- and pixel-bounded with the
  header checked BEFORE full decode
"""

import sqlite3
from pathlib import Path

import pytest
from enrichment_fakes import (
    EnrichmentStorageError,
    ExternalIdentityResolverPort,
    FakeAlbumProvider,
    FakeArtistProvider,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)
from PySide6.QtCore import QBuffer, QIODevice, QSize
from PySide6.QtGui import QImage

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistCandidate,
    ArtistExternalIdentity,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
    IdentityResolutionStatus,
    IdentityStatus,
    LocalAlbumEvidence,
    MatchMethod,
    resolve_album_identity,
    resolve_artist_identity,
)
from michi.infrastructure.enrichment_assets import (
    MAX_EXTERNAL_IMAGE_BYTES,
    MAX_EXTERNAL_IMAGE_HEIGHT,
    MAX_EXTERNAL_IMAGE_PIXELS,
    MAX_EXTERNAL_IMAGE_WIDTH,
    FilesystemEnrichmentAssetStore,
    _dimensions_allowed,
)
from michi.infrastructure.enrichment_repository import (
    CURRENT_ENRICHMENT_SCHEMA,
    EnrichmentSchemaError,
    SqliteEnrichmentRepository,
)


def make_service(resolver=None, repository=None, identity_repository=None):
    return EnrichmentService(
        resolver=resolver or FakeIdentityResolverStub(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=repository or RecordingKnowledgeRepository(),
        identity_repository=identity_repository or InMemoryIdentityRepository(),
    )


class FakeIdentityResolverStub(ExternalIdentityResolverPort):
    """Never returns candidates (hint-driven flows only)."""

    def __init__(self):
        self.artist_evidence: list = []
        self.group_evidence: list = []

    def find_artist_candidates(self, evidence):
        self.artist_evidence.append(evidence)
        return ()

    def find_release_group_candidates(self, evidence):
        self.group_evidence.append(evidence)
        return ()

    def find_release_edition_candidates(self, evidence):
        return ()


class ScriptedResolver(ExternalIdentityResolverPort):
    """Queue of candidate batches for authority-precedence scenarios."""

    def __init__(self):
        self.artist_batches: list[tuple] = []
        self.group_batches: list[tuple] = []
        self.artist_calls = 0

    def find_artist_candidates(self, evidence):
        self.artist_calls += 1
        batch = self.artist_batches.pop(0) if self.artist_batches else ()
        return tuple(batch)

    def find_release_group_candidates(self, evidence):
        batch = self.group_batches.pop(0) if self.group_batches else ()
        return tuple(batch)

    def find_release_edition_candidates(self, evidence):
        return ()


def artist_evidence(name="Artist A", mbids=(), albums=()):
    return ArtistIdentityEvidence(
        local_artist_key=name.casefold(),
        local_artist_name=name,
        known_albums=tuple(
            LocalAlbumEvidence(a[0], a[1] if len(a) > 1 else 0) for a in albums
        ),
        identity_hints=ArtistIdentityHints(artist_ids=tuple(mbids)),
    )


def album_evidence(key="album-a", title="Album X", rg_ids=()):
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title=title,
        identity_hints=AlbumIdentityHints(release_group_ids=tuple(rg_ids)),
    )


def matching_candidate(mbid, name="Artist A", album=("Album One", 1980)):
    return ArtistCandidate(
        external_artist_id=mbid,
        canonical_name=name,
        known_albums=(LocalAlbumEvidence(album[0], album[1]),),
    )


class TestPersistentIdentityInvariants:
    def test_artist_valid_resolved_accepted(self):
        identity = ArtistExternalIdentity(
            local_artist_key="the cure", external_artist_id="mb-x"
        )
        assert identity.status is IdentityStatus.RESOLVED

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"local_artist_key": "", "external_artist_id": "mb-x"},
            {"local_artist_key": "k", "external_artist_id": ""},
            {
                "local_artist_key": "k",
                "external_artist_id": "mb-x",
                "status": IdentityStatus.AMBIGUOUS,
            },
            {
                "local_artist_key": "k",
                "external_artist_id": "mb-x",
                "status": IdentityStatus.IDENTITY_CONFLICT,
            },
            {
                "local_artist_key": "k",
                "external_artist_id": "mb-x",
                "status": IdentityStatus.NOT_FOUND,
            },
        ],
    )
    def test_artist_impossible_states_rejected(self, kwargs):
        with pytest.raises(ValueError):
            ArtistExternalIdentity(**kwargs)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"local_album_key": "", "release_group_id": "rg-x"},
            {"local_album_key": "k", "release_group_id": ""},
            {
                "local_album_key": "k",
                "release_group_id": "rg-x",
                "status": IdentityStatus.AMBIGUOUS,
            },
        ],
    )
    def test_album_impossible_states_rejected(self, kwargs):
        with pytest.raises(ValueError):
            AlbumExternalIdentity(**kwargs)

    def test_album_empty_release_id_allowed(self):
        identity = AlbumExternalIdentity(
            local_album_key="k", release_group_id="rg-x", release_id=""
        )
        assert identity.release_id == ""


class TestDuplicateHintNormalization:
    def test_artist_identical_duplicates_not_conflict(self):
        evidence = artist_evidence(mbids=("mb-a", "mb-a"))
        resolution = resolve_artist_identity([], evidence)
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_artist_duplicates_plus_distinct_conflict(self):
        evidence = artist_evidence(mbids=("mb-a", "mb-a", "mb-b"))
        resolution = resolve_artist_identity([], evidence)
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_release_group_duplicates_normalized(self):
        resolution = resolve_album_identity(
            [], [], album_evidence(rg_ids=("rg-a", "rg-a"))
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"

    def test_release_group_distinct_conflict(self):
        resolution = resolve_album_identity(
            [], [], album_evidence(rg_ids=("rg-a", "rg-b"))
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_release_duplicates_normalized_not_conflict(self):
        resolution = resolve_album_identity(
            [],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="",
                identity_hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-a", "rel-a")
                ),
            ),
        )
        # One release hint: subject to normal corroboration (no edition
        # candidates -> not assigned), NOT a conflict.
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_release_distinct_conflict(self):
        resolution = resolve_album_identity(
            [],
            [],
            AlbumIdentityEvidence(
                local_album_key="album-a",
                local_album_title="",
                identity_hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-a", "rel-b")
                ),
            ),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT


class TestAuthorityPrecedence:
    def test_manual_short_circuits_ambiguous_evidence(self):
        resolver = ScriptedResolver()
        service = make_service(resolver=resolver)
        service.confirm_artist_identity("artist a", "mb-manual")
        outcome = service.request_artist_enrichment(artist_evidence())
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-manual"
        assert resolver.artist_calls == 0

    def test_embedded_survives_weaker_auto(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="artist a",
                external_artist_id="mb-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()
        # Resolver would return an AUTO candidate for a DIFFERENT id.
        resolver.artist_batches.append((matching_candidate("mb-y"),))
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_artist_enrichment(artist_evidence())
        assert resolver.artist_calls == 0  # short-circuited
        assert outcome.request.external_entity_id == "mb-x"

    def test_embedded_same_explicit_hint_retained(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="artist a",
                external_artist_id="mb-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        service = make_service(identity_repository=identity_repo)
        outcome = service.request_artist_enrichment(artist_evidence(mbids=("mb-x",)))
        assert outcome.request.external_entity_id == "mb-x"
        identity = identity_repo.load_artist_identity("artist a")
        assert identity.match_method is MatchMethod.EMBEDDED_HINT

    def test_embedded_changed_explicit_hint_transitions(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="artist a",
                external_artist_id="mb-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        service = make_service(
            resolver=FakeIdentityResolverStub(),
            repository=knowledge,
            identity_repository=identity_repo,
        )
        knowledge.save_artist_profile(
            FakeArtistProvider().fetch_profile("artist a", "mb-x")
        )
        outcome = service.request_artist_enrichment(artist_evidence(mbids=("mb-y",)))
        assert outcome.request.external_entity_id == "mb-y"
        # Direct embedded evidence changed: old knowledge invalidated.
        assert knowledge.load_artist_profile("artist a") is None
        assert (
            identity_repo.load_artist_identity("artist a").external_artist_id == "mb-y"
        )

    def test_embedded_conflicting_explicit_hints_revoke(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="artist a",
                external_artist_id="mb-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        service = make_service(
            resolver=FakeIdentityResolverStub(),
            repository=knowledge,
            identity_repository=identity_repo,
        )
        knowledge.save_artist_profile(
            FakeArtistProvider().fetch_profile("artist a", "mb-x")
        )
        outcome = service.request_artist_enrichment(
            artist_evidence(mbids=("mb-x", "mb-y"))
        )
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        # Old non-manual authority revoked.
        assert identity_repo.load_artist_identity("artist a") is None
        assert knowledge.load_artist_profile("artist a") is None

    def test_album_embedded_survives_weaker_auto(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X")
        )
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "rg-x"


class TestAutoRevocation:
    def _auto_service(self, knowledge, identity_repo, resolver):
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        # Establish AUTO X + knowledge X.
        resolver.artist_batches.append((matching_candidate("mb-x"),))
        first = service.request_artist_enrichment(
            artist_evidence(name="Artist A", albums=(("Album One", 1980),))
        )
        service.deliver_artist_profile(
            first.request, service._artist_provider.fetch_profile("artist a", "mb-x")
        )
        assert (
            identity_repo.load_artist_identity("artist a").external_artist_id == "mb-x"
        )
        assert knowledge.load_artist_profile("artist a") is not None
        return first

    def test_auto_to_ambiguous_revoked(self):
        knowledge = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        resolver = ScriptedResolver()
        first = self._auto_service(knowledge, identity_repo, resolver)
        # Fresh evidence: two tied candidates -> AMBIGUOUS.
        resolver.artist_batches.append(
            (
                matching_candidate("mb-x"),
                matching_candidate("mb-y"),
            )
        )
        outcome = service_request_ambiguous(resolver, identity_repo, knowledge)
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert identity_repo.load_artist_identity("artist a") is None
        assert knowledge.load_artist_profile("artist a") is None
        # Late old result is STALE.
        assert (
            service_request_ambiguous_last(first, knowledge, identity_repo)
            is DeliveryVerdict.STALE
        )

    def test_auto_to_no_match_revoked(self):
        knowledge = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        resolver = ScriptedResolver()
        self._auto_service(knowledge, identity_repo, resolver)
        resolver.artist_batches.append(())  # no candidates -> NO_MATCH
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", albums=(("Album One", 1980),))
        )
        assert outcome.resolution.status is IdentityResolutionStatus.NO_MATCH
        assert identity_repo.load_artist_identity("artist a") is None
        assert knowledge.load_artist_profile("artist a") is None

    def test_auto_to_conflict_revoked(self):
        knowledge = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        resolver = ScriptedResolver()
        self._auto_service(knowledge, identity_repo, resolver)
        outcome = service_with_conflicting_hints(identity_repo, knowledge)
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert identity_repo.load_artist_identity("artist a") is None

    def test_auto_same_id_preserved(self):
        knowledge = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        resolver = ScriptedResolver()
        self._auto_service(knowledge, identity_repo, resolver)
        resolver.artist_batches.append((matching_candidate("mb-x"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", albums=(("Album One", 1980),))
        )
        assert outcome.request.external_entity_id == "mb-x"
        assert knowledge.load_artist_profile("artist a") is not None

    def test_auto_different_id_transitioned(self):
        knowledge = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        resolver = ScriptedResolver()
        self._auto_service(knowledge, identity_repo, resolver)
        resolver.artist_batches.append((matching_candidate("mb-z"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_artist_enrichment(
            artist_evidence(name="Artist A", albums=(("Album One", 1980),))
        )
        assert outcome.request.external_entity_id == "mb-z"
        assert knowledge.load_artist_profile("artist a") is None
        assert (
            identity_repo.load_artist_identity("artist a").external_artist_id == "mb-z"
        )


def service_request_ambiguous(resolver, identity_repo, knowledge):
    service = make_service(
        resolver=resolver, repository=knowledge, identity_repository=identity_repo
    )
    return service.request_artist_enrichment(
        artist_evidence(name="Artist A", albums=(("Album One", 1980),))
    )


def service_request_ambiguous_last(first, knowledge, identity_repo):
    service = make_service(
        resolver=ScriptedResolver(),
        repository=knowledge,
        identity_repository=identity_repo,
    )
    profile = service._artist_provider.fetch_profile("artist a", "mb-x")
    return service.deliver_artist_profile(first.request, profile)


def service_with_conflicting_hints(identity_repo, knowledge):
    service = make_service(
        resolver=FakeIdentityResolverStub(),
        repository=knowledge,
        identity_repository=identity_repo,
    )
    return service.request_artist_enrichment(
        artist_evidence(name="Artist A", mbids=("mb-x", "mb-y"))
    )


class TestMalformedIdentityReads:
    def _insert_row(self, db_path: Path, row: tuple) -> SqliteEnrichmentRepository:
        repo = SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?)", row)
            conn.commit()
        finally:
            conn.close()
        return repo

    def test_malformed_match_method_raises(self, tmp_path):
        repo = self._insert_row(
            tmp_path / "enrichment.db",
            ("bad-key", "mb-x", "RESOLVED", "INVALID_METHOD", "when"),
        )
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("bad-key")

    def test_non_resolved_persistent_status_raises(self, tmp_path):
        repo = self._insert_row(
            tmp_path / "enrichment.db",
            ("bad-key", "mb-x", "AMBIGUOUS", "AUTO", "when"),
        )
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("bad-key")

    def test_empty_external_id_raises(self, tmp_path):
        repo = self._insert_row(
            tmp_path / "enrichment.db",
            ("bad-key", "", "RESOLVED", "AUTO", "when"),
        )
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("bad-key")

    def test_bulk_load_partial_corruption_raises(self, tmp_path):
        repo = self._insert_row(
            tmp_path / "enrichment.db",
            ("bad-key", "mb-x", "RESOLVED", "INVALID_METHOD", "when"),
        )
        repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="good-key", external_artist_id="mb-good"
            )
        )
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identities()

    def test_corrupt_identity_never_triggers_auto(self):
        # Simulate corruption: load raises storage error.
        class CorruptRepo(InMemoryIdentityRepository):
            def load_artist_identity(self, local_artist_key):
                raise EnrichmentStorageError("corrupt")

        resolver = FakeIdentityResolverStub()
        service = make_service(resolver=resolver, identity_repository=CorruptRepo())
        with pytest.raises(EnrichmentStorageError):
            service.request_artist_enrichment(artist_evidence(mbids=("mb-a",)))
        assert len(resolver.artist_evidence) == 0
        assert service.pending_count() == 0


class TestMigrationShapeFailClosed:
    def _meta_only_v2(self, db_path: Path) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE enrichment_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "2"),
            )
            conn.commit()
        finally:
            conn.close()

    def _add_v2_identity(self, db_path: Path, table: str, columns: str) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(f"CREATE TABLE {table} ({columns})")
            conn.commit()
        finally:
            conn.close()

    def _master(self, db_path: Path) -> list:
        conn = sqlite3.connect(str(db_path))
        try:
            return conn.execute(
                "SELECT type, name FROM sqlite_master ORDER BY name"
            ).fetchall()
        finally:
            conn.close()

    _ARTIST_V2 = (
        "local_artist_key TEXT PRIMARY KEY,"
        "external_artist_id TEXT NOT NULL,"
        "status TEXT NOT NULL,"
        "match_method TEXT NOT NULL,"
        "manually_confirmed INTEGER NOT NULL,"
        "resolved_at TEXT NOT NULL"
    )
    _ALBUM_V2 = (
        "local_album_key TEXT PRIMARY KEY,"
        "release_group_id TEXT NOT NULL,"
        "release_id TEXT NOT NULL,"
        "status TEXT NOT NULL,"
        "match_method TEXT NOT NULL,"
        "manually_confirmed INTEGER NOT NULL,"
        "resolved_at TEXT NOT NULL"
    )

    def test_v2_artist_only_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._meta_only_v2(db_path)
        self._add_v2_identity(db_path, "artist_identity", self._ARTIST_V2)
        before = self._master(db_path)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert self._master(db_path) == before

    def test_v2_album_only_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._meta_only_v2(db_path)
        self._add_v2_identity(db_path, "album_identity", self._ALBUM_V2)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_v2_no_identity_tables_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._meta_only_v2(db_path)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_v2_wrong_column_shape_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._meta_only_v2(db_path)
        self._add_v2_identity(db_path, "artist_identity", self._ARTIST_V2)
        # Album table missing the legacy boolean.
        self._add_v2_identity(
            db_path,
            "album_identity",
            self._ALBUM_V2.replace("manually_confirmed INTEGER NOT NULL,", ""),
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_v3_with_legacy_column_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "ALTER TABLE artist_identity "
                "ADD COLUMN manually_confirmed INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_v1_with_unexpected_identity_table_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        self._meta_only_v2(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE enrichment_meta SET value = '1' "
                "WHERE key = 'enrichment_schema_version'"
            )
            conn.commit()
        finally:
            conn.close()
        self._add_v2_identity(db_path, "artist_identity", self._ARTIST_V2)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)


class TestVersionTruth:
    def test_valid_version(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

    @pytest.mark.parametrize("corrupt_value", ["banana", "0", "-1"])
    def test_malformed_version_raises(self, tmp_path, corrupt_value):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE enrichment_meta SET value = ? "
                "WHERE key = 'enrichment_schema_version'",
                (corrupt_value,),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            repo.version()

    def test_missing_version_row_raises(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        repo = SqliteEnrichmentRepository(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "DELETE FROM enrichment_meta WHERE key = 'enrichment_schema_version'"
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            repo.version()


class TestImageDimensionPolicy:
    def test_constants_are_documented_values(self):
        assert MAX_EXTERNAL_IMAGE_BYTES == 10 * 1024 * 1024
        assert MAX_EXTERNAL_IMAGE_WIDTH == 8192
        assert MAX_EXTERNAL_IMAGE_HEIGHT == 8192
        assert MAX_EXTERNAL_IMAGE_PIXELS == 20_000_000

    @pytest.mark.parametrize(
        ("width", "height", "allowed"),
        [
            (1, 1, True),
            (4096, 4096, True),
            (8192, 8192, False),  # pixel cap (67M > 20M)
            (9000, 100, False),  # width cap
            (100, 9000, False),  # height cap
            (0, 100, False),
            (-1, 100, False),
            (100, 0, False),
        ],
    )
    def test_dimensions_allowed_matrix(self, width, height, allowed):
        assert _dimensions_allowed(width, height) is allowed

    def test_oversized_header_rejected_before_decode(self, tmp_path, monkeypatch):
        import michi.infrastructure.enrichment_assets as assets_module

        class FakeReader:
            def __init__(self):
                self.read_called = False

            def setDecideFormatFromContent(self, value):  # noqa: N802
                pass

            def setDevice(self, device):  # noqa: N802
                pass

            def canRead(self):  # noqa: N802
                return True

            def size(self):  # noqa: N802
                return QSize(9000, 100)

            def read(self):  # noqa: N802
                self.read_called = True
                raise AssertionError("full decode must not run")

        fake = FakeReader()
        monkeypatch.setattr(assets_module, "QImageReader", lambda: fake)

        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        data = self._png_bytes()
        record = assets_module.EnrichmentAssetRecord(
            asset_id="cover-1",
            entity_kind=assets_module.EnrichmentEntityKind.ARTIST,
            external_entity_id="mb-a",
            mime_type="image/png",
        )
        assert store.store(record, data) is None
        assert fake.read_called is False

    @staticmethod
    def _png_bytes() -> bytes:
        image = QImage(8, 6, QImage.Format_RGB32)
        image.fill(0xFF8844)
        buffer = QBuffer()
        assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        assert image.save(buffer, "PNG")
        return bytes(buffer.data())

    def test_normal_png_still_stores(self, tmp_path):
        import hashlib

        from michi.domain.enrichment import (
            EnrichmentAssetRecord,
            EnrichmentEntityKind,
        )

        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        data = self._png_bytes()
        result = store.store(
            EnrichmentAssetRecord(
                asset_id="cover-1",
                entity_kind=EnrichmentEntityKind.ARTIST,
                external_entity_id="mb-a",
                mime_type="image/png",
            ),
            data,
        )
        assert result is not None
        assert (result.width, result.height) == (8, 6)
        assert result.checksum == hashlib.sha256(data).hexdigest()
        assert store.path_for("cover-1") is not None
        record = store.record_for("cover-1")
        assert record is not None
        assert record.checksum == result.checksum
