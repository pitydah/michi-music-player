"""M6.9A-R3.2 — migration + identity authority final seal regressions.

Five required test groups:
1. Migration commit gate (post-migration V3 validation BEFORE COMMIT;
   V2 semantic authority-row validation; rollback proofs)
2. SQLite constraint validation (canonical PRAGMA signature)
3. Release-edition contradiction detection
4. Album match-authority parity matrix
5. Identity corruption / version / whitespace hygiene
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

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistExternalIdentity,
    DeliveryVerdict,
    IdentityResolutionStatus,
    MatchMethod,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
    dedupe_identity_ids,
    resolve_release_hint_for_group,
)
from michi.infrastructure.enrichment_repository import (
    CURRENT_ENRICHMENT_SCHEMA,
    EnrichmentSchemaError,
    SqliteEnrichmentRepository,
)

V1_TABLES_SQL = (
    "CREATE TABLE artist_knowledge ("
    "local_artist_key TEXT PRIMARY KEY,"
    "profile TEXT NOT NULL)",
    "CREATE TABLE album_knowledge ("
    "local_album_key TEXT PRIMARY KEY,"
    "profile TEXT NOT NULL)",
    "CREATE TABLE enrichment_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
)

V2_IDENTITY_SQL = (
    "CREATE TABLE artist_identity ("
    "local_artist_key TEXT PRIMARY KEY,"
    "external_artist_id TEXT NOT NULL,"
    "status TEXT NOT NULL,"
    "match_method TEXT NOT NULL,"
    "manually_confirmed INTEGER NOT NULL,"
    "resolved_at TEXT NOT NULL)",
    "CREATE TABLE album_identity ("
    "local_album_key TEXT PRIMARY KEY,"
    "release_group_id TEXT NOT NULL,"
    "release_id TEXT NOT NULL,"
    "status TEXT NOT NULL,"
    "match_method TEXT NOT NULL,"
    "manually_confirmed INTEGER NOT NULL,"
    "resolved_at TEXT NOT NULL)",
)


def _exec_many(db_path: Path, statements: tuple) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for statement in statements:
            if isinstance(statement, tuple):
                conn.execute(statement[0], statement[1])
            else:
                conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def _create_v2_db(db_path: Path, artist_row=None, album_row=None) -> None:
    _exec_many(
        db_path,
        (
            *V1_TABLES_SQL,
            *V2_IDENTITY_SQL,
            (
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "2"),
            ),
        ),
    )
    if artist_row is not None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?, ?)", artist_row
            )
            conn.commit()
        finally:
            conn.close()
    if album_row is not None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO album_identity VALUES(?, ?, ?, ?, ?, ?, ?)", album_row
            )
            conn.commit()
        finally:
            conn.close()


def _master(db_path: Path) -> list:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT type, name FROM sqlite_master ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def _version_row(db_path: Path) -> str | None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT value FROM enrichment_meta WHERE key = 'enrichment_schema_version'"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _valid_v2_artist_row():
    return ("the cure", "mb-cure", "RESOLVED", "MANUAL", 1, "when")


def _valid_v2_album_row():
    return ("album-a", "rg-a", "", "RESOLVED", "AUTO", 0, "when")


class ScriptedResolver(ExternalIdentityResolverPort):
    def __init__(self):
        self.artist_batches: list[tuple] = []
        self.group_batches: list[tuple] = []
        self.edition_batches: list[tuple] = []
        self.artist_calls = 0

    def find_artist_candidates(self, evidence):
        self.artist_calls += 1
        batch = self.artist_batches.pop(0) if self.artist_batches else ()
        return tuple(batch)

    def find_release_group_candidates(self, evidence):
        batch = self.group_batches.pop(0) if self.group_batches else ()
        return tuple(batch)

    def find_release_edition_candidates(self, evidence):
        batch = self.edition_batches.pop(0) if self.edition_batches else ()
        return tuple(batch)


def make_service(resolver=None, repository=None, identity_repository=None):
    return EnrichmentService(
        resolver=resolver or ScriptedResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=repository or RecordingKnowledgeRepository(),
        identity_repository=identity_repository or InMemoryIdentityRepository(),
    )


def album_evidence(key="album-a", rg_ids=(), release_ids=(), title="", artist_name=""):
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title=title,
        local_album_artist_name=artist_name,
        identity_hints=AlbumIdentityHints(
            release_group_ids=tuple(rg_ids), release_ids=tuple(release_ids)
        ),
    )


def auto_group(mbid, title="Album X", artist="Artist A", year=1980):
    return ReleaseGroupCandidate(
        release_group_id=mbid,
        title=title,
        artist_credit_names=(artist,),
        first_release_year=year,
    )


# ---------------------------------------------------------------------------
# GROUP 1 — MIGRATION COMMIT GATE
# ---------------------------------------------------------------------------


class TestMigrationCommitGate:
    def test_v1_valid_migration_pass(self, tmp_path):
        _exec_many(tmp_path / "enrichment.db", V1_TABLES_SQL)
        conn = sqlite3.connect(str(tmp_path / "enrichment.db"))
        try:
            conn.execute(
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "1"),
            )
            conn.commit()
        finally:
            conn.close()
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

    def test_v2_valid_migration_pass(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(db_path, _valid_v2_artist_row(), _valid_v2_album_row())
        repo = SqliteEnrichmentRepository(db_path)
        assert repo.version() == 3
        assert repo.load_artist_identity("the cure") is not None
        assert repo.load_album_identity("album-a") is not None

    @pytest.mark.parametrize("drop_table", ["artist_knowledge", "album_knowledge"])
    def test_v2_missing_knowledge_table_rejected_rolled_back(
        self, tmp_path, drop_table
    ):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(db_path, _valid_v2_artist_row(), _valid_v2_album_row())
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(f"DROP TABLE {drop_table}")
            conn.commit()
        finally:
            conn.close()
        before = _master(db_path)
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"
        assert _master(db_path) == before

    @pytest.mark.parametrize(
        ("artist_row", "album_row"),
        [
            # semantically malformed artist rows
            (("k", "mb-x", "AMBIGUOUS", "AUTO", 0, "when"), None),
            (("k", "mb-x", "RESOLVED", "INVALID", 0, "when"), None),
            (("k", "", "RESOLVED", "AUTO", 0, "when"), None),
            # semantically malformed album rows
            (None, ("k", "rg-x", "", "AMBIGUOUS", "AUTO", 0, "when")),
            (None, ("k", "rg-x", "", "RESOLVED", "INVALID", 0, "when")),
            (None, ("k", "", "", "RESOLVED", "AUTO", 0, "when")),
        ],
    )
    def test_v2_semantically_malformed_row_rejected_rolled_back(
        self, tmp_path, artist_row, album_row
    ):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(
            db_path,
            artist_row if artist_row is not None else _valid_v2_artist_row(),
            album_row if album_row is not None else _valid_v2_album_row(),
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"
        # The malformed authority row was NOT deleted or normalized.
        conn = sqlite3.connect(str(db_path))
        try:
            if artist_row is not None:
                assert (
                    conn.execute("SELECT COUNT(*) FROM artist_identity").fetchone()[0]
                    == 1
                )
            if album_row is not None:
                assert (
                    conn.execute("SELECT COUNT(*) FROM album_identity").fetchone()[0]
                    == 1
                )
        finally:
            conn.close()

    def test_v2_empty_album_release_id_allowed(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(db_path, _valid_v2_artist_row(), _valid_v2_album_row())
        repo = SqliteEnrichmentRepository(db_path)
        assert repo.load_album_identity("album-a").release_id == ""

    def test_post_migration_validation_failure_rolls_back(self, tmp_path, monkeypatch):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(db_path, _valid_v2_artist_row(), _valid_v2_album_row())
        before = _master(db_path)

        def fail_validation(self, conn):
            raise EnrichmentSchemaError("injected post-migration failure")

        monkeypatch.setattr(
            SqliteEnrichmentRepository, "_validate_current_schema", fail_validation
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        # ROLLBACK: version still 2, source tables intact, no _v3 temp.
        assert _version_row(db_path) == "2"
        assert _master(db_path) == before
        assert not any("_v3" in row[1] for row in _master(db_path))


# ---------------------------------------------------------------------------
# GROUP 2 — SQLITE CONSTRAINT VALIDATION
# ---------------------------------------------------------------------------


class TestSqliteConstraintValidation:
    def _rebuild_identity_table(self, db_path: Path, table: str, ddl: str) -> None:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(f"DROP TABLE {table}")
            conn.execute(ddl)
            conn.commit()
        finally:
            conn.close()

    def test_fresh_canonical_schema_validates(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.version() == 3

    def test_artist_identity_without_primary_key_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "artist_identity",
            "CREATE TABLE artist_identity ("
            "local_artist_key TEXT,"
            "external_artist_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_album_identity_without_primary_key_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "album_identity",
            "CREATE TABLE album_identity ("
            "local_album_key TEXT,"
            "release_group_id TEXT NOT NULL,"
            "release_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_nullable_external_artist_id_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "artist_identity",
            "CREATE TABLE artist_identity ("
            "local_artist_key TEXT PRIMARY KEY,"
            "external_artist_id TEXT,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_nullable_release_group_id_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "album_identity",
            "CREATE TABLE album_identity ("
            "local_album_key TEXT PRIMARY KEY,"
            "release_group_id TEXT,"
            "release_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_wrong_declared_type_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "artist_identity",
            "CREATE TABLE artist_identity ("
            "local_artist_key TEXT PRIMARY KEY,"
            "external_artist_id INTEGER NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)

    def test_meta_key_without_primary_key_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        SqliteEnrichmentRepository(db_path)
        self._rebuild_identity_table(
            db_path,
            "enrichment_meta",
            "CREATE TABLE enrichment_meta (key TEXT, value TEXT NOT NULL)",
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)


# ---------------------------------------------------------------------------
# GROUP 3 — RELEASE-EDITION CONTRADICTIONS
# ---------------------------------------------------------------------------


class TestReleaseContradictions:
    def _resolve(self, hint, candidates, group="rg-a"):
        return resolve_release_hint_for_group(group, hint, candidates)

    def test_single_correct_mapping_accepted(self):
        status, release_id = self._resolve(
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),),
        )
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == "rel-x"

    def test_duplicate_same_mapping_accepted(self):
        status, release_id = self._resolve(
            "rel-x",
            (
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
            ),
        )
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == "rel-x"

    def test_wrong_group_conflict(self):
        status, release_id = self._resolve(
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-b"),),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_same_release_multiple_groups_conflict(self):
        status, release_id = self._resolve(
            "rel-x",
            (
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-b"),
            ),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_no_matching_candidate_not_assigned(self):
        status, release_id = self._resolve("rel-x", ())
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == ""

    def test_unrelated_candidates_ignored(self):
        status, release_id = self._resolve(
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-y", release_group_id="rg-b"),),
        )
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == ""


# ---------------------------------------------------------------------------
# GROUP 4 — ALBUM MATCH-AUTHORITY PARITY
# ---------------------------------------------------------------------------


class TestAlbumAuthority:
    def test_manual_survives_ambiguous(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.MANUAL,
            )
        )
        resolver = ScriptedResolver()
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X", artist_name="Artist A")
        )
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "rg-x"

    def test_embedded_no_direct_hints_short_circuit(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-y"),))
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(album_evidence(key="album-a"))
        assert outcome.request.external_entity_id == "rg-x"
        # Resolver never consulted: the AUTO batch remains unconsumed —
        # weaker AUTO evidence cannot replace EMBEDDED authority.
        assert len(resolver.group_batches) == 1

    def test_embedded_release_only_hint_refines(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()
        resolver.edition_batches.append(
            (ReleaseEditionCandidate(release_id="rel-a", release_group_id="rg-x"),)
        )
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", release_ids=("rel-a",))
        )
        assert outcome.request.external_entity_id == "rg-x"
        assert outcome.request.external_variant_id == "rel-a"
        identity = identity_repo.load_album_identity("album-a")
        assert identity.release_id == "rel-a"
        assert identity.match_method is MatchMethod.EMBEDDED_HINT

    def test_embedded_release_changed_transitions_and_invalidates(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                release_id="rel-a",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        service = make_service(
            resolver=ScriptedResolver(),
            repository=knowledge,
            identity_repository=identity_repo,
        )
        knowledge.save_album_profile(
            FakeAlbumProvider().fetch_profile("album-a", "rg-x", "rel-a")
        )
        resolver = ScriptedResolver()
        resolver.edition_batches.append(
            (ReleaseEditionCandidate(release_id="rel-b", release_group_id="rg-x"),)
        )
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", release_ids=("rel-b",))
        )
        assert outcome.request.external_variant_id == "rel-b"
        assert knowledge.load_album_profile("album-a") is None

    def test_embedded_release_wrong_group_conflict_revokes(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()
        resolver.edition_batches.append(
            (ReleaseEditionCandidate(release_id="rel-a", release_group_id="rg-y"),)
        )
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", release_ids=("rel-a",))
        )
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert identity_repo.load_album_identity("album-a") is None

    def test_embedded_release_uncorroborated_group_preserved(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.EMBEDDED_HINT,
            )
        )
        resolver = ScriptedResolver()  # no edition candidates
        service = make_service(resolver=resolver, identity_repository=identity_repo)
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", release_ids=("rel-a",))
        )
        assert outcome.request.external_entity_id == "rg-x"
        assert outcome.request.external_variant_id == ""
        identity = identity_repo.load_album_identity("album-a")
        assert identity.release_id == ""

    def test_auto_same_preserved(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-x"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X", artist_name="Artist A")
        )
        assert outcome.request.external_entity_id == "rg-x"
        assert identity_repo.load_album_identity("album-a") is not None

    def test_auto_different_transitions(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-z"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X", artist_name="Artist A")
        )
        assert outcome.request.external_entity_id == "rg-z"

    @pytest.mark.parametrize("batch", [(), (auto_group("rg-a"), auto_group("rg-b"))])
    def test_auto_unresolved_revoked(self, batch):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        resolver = ScriptedResolver()
        resolver.group_batches.append(batch)
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X", artist_name="Artist A")
        )
        assert outcome.request is None
        assert identity_repo.load_album_identity("album-a") is None

    def test_auto_conflict_revoked_and_late_result_stale(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-x"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        first = service.request_album_enrichment(
            album_evidence(key="album-a", title="Album X", artist_name="Artist A")
        )
        service.deliver_album_profile(
            first.request, service._album_provider.fetch_profile("album-a", "rg-x")
        )
        # Now direct conflicting hints revoke the AUTO mapping.
        conflicting = make_service(
            resolver=ScriptedResolver(),
            repository=knowledge,
            identity_repository=identity_repo,
        )
        outcome = conflicting.request_album_enrichment(
            album_evidence(key="album-a", rg_ids=("rg-x", "rg-y"))
        )
        assert outcome.request is None
        assert identity_repo.load_album_identity("album-a") is None
        assert knowledge.load_album_profile("album-a") is None
        # Late old result: STALE, zero writes.
        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            conflicting.deliver_album_profile(first.request, profile)
            is DeliveryVerdict.STALE
        )


# ---------------------------------------------------------------------------
# GROUP 5 — CORRUPTION / VERSION / WHITESPACE HYGIENE
# ---------------------------------------------------------------------------


class TestCorruptionAndHygiene:
    def test_invalid_status_type_construction_value_error(self):
        with pytest.raises(ValueError):
            ArtistExternalIdentity(
                local_artist_key="k",
                external_artist_id="mb-x",
                status="AMBIGUOUS",  # wrong TYPE, not wrong enum member
            )

    def test_invalid_match_method_construction_value_error(self):
        with pytest.raises(ValueError):
            ArtistExternalIdentity(
                local_artist_key="k",
                external_artist_id="mb-x",
                match_method="MANUAL",  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        ("kwargs",),
        [
            ({"local_artist_key": "   ", "external_artist_id": "mb-x"},),
            ({"local_artist_key": "k", "external_artist_id": "   "},),
        ],
    )
    def test_whitespace_only_artist_ids_rejected(self, kwargs):
        with pytest.raises(ValueError):
            ArtistExternalIdentity(**kwargs)

    def test_whitespace_only_album_ids_rejected(self):
        with pytest.raises(ValueError):
            AlbumExternalIdentity(local_album_key="   ", release_group_id="rg-x")
        with pytest.raises(ValueError):
            AlbumExternalIdentity(local_album_key="k", release_group_id="   ")

    def test_malformed_row_type_raises_storage_error(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        conn = sqlite3.connect(str(tmp_path / "enrichment.db"))
        try:
            # status stored as a non-string type that cannot enum-index.
            conn.execute(
                "INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?)",
                ("bad-key", "mb-x", 123, "AUTO", "when"),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("bad-key")

    def test_single_load_key_mismatch_raises(self, tmp_path, monkeypatch):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        repo.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key="good-key", external_artist_id="mb-x"
            )
        )
        original = SqliteEnrichmentRepository._artist_identity_from_row

        def mismatching(self, row):
            identity = original(row)
            return ArtistExternalIdentity(
                local_artist_key="other-key",
                external_artist_id=identity.external_artist_id,
            )

        monkeypatch.setattr(
            SqliteEnrichmentRepository, "_artist_identity_from_row", mismatching
        )
        with pytest.raises(EnrichmentStorageError):
            repo.load_artist_identity("good-key")

    def test_hint_whitespace_normalization(self):
        assert dedupe_identity_ids((" mb-a ", "mb-a", "   ")) == ("mb-a",)
        assert dedupe_identity_ids((" rg-a ", "rg-a")) == ("rg-a",)
        assert dedupe_identity_ids((" rel-a ", "rel-a")) == ("rel-a",)

    def test_version_future_raises(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        conn = sqlite3.connect(str(tmp_path / "enrichment.db"))
        try:
            conn.execute(
                "UPDATE enrichment_meta SET value = ? "
                "WHERE key = 'enrichment_schema_version'",
                (str(CURRENT_ENRICHMENT_SCHEMA + 1),),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            repo.version()
