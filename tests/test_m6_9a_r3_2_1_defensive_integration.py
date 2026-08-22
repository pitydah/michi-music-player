"""M6.9A-R3.2.1 — final defensive input + integration seal regressions.

Six required test groups:
A. Release defensive input (malformed matching edition candidates)
B. Persistent identity runtime string-type safety
C. SQLite identity corruption (wrong runtime types)
D. V2 semantic source (resolved_at + legacy manually_confirmed)
E. Album knowledge authority (preservation/invalidation + same-service
   ledger proof)
F. Transactional brand-new database initialization
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


def _exec(db_path: Path, statements) -> None:
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
    _exec(
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


def _version_row(db_path: Path) -> str | None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT value FROM enrichment_meta WHERE key = 'enrichment_schema_version'"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


class ScriptedResolver(ExternalIdentityResolverPort):
    def __init__(self):
        self.group_batches: list[tuple] = []
        self.edition_batches: list[tuple] = []

    def find_artist_candidates(self, evidence):
        return ()

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


def auto_group(mbid):
    return ReleaseGroupCandidate(
        release_group_id=mbid,
        title="Album X",
        artist_credit_names=("Artist A",),
        first_release_year=1980,
    )


def album_evidence(rg_ids=(), release_ids=()):
    return AlbumIdentityEvidence(
        local_album_key="album-a",
        local_album_title="Album X",
        local_album_artist_name="Artist A",
        identity_hints=AlbumIdentityHints(
            release_group_ids=tuple(rg_ids), release_ids=tuple(release_ids)
        ),
    )


# ---------------------------------------------------------------------------
# GROUP A — RELEASE DEFENSIVE INPUT
# ---------------------------------------------------------------------------


class TestReleaseDefensiveInput:
    def test_matching_blank_group_conflict(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-x", release_group_id=""),),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_matching_whitespace_group_conflict(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-x", release_group_id="   "),),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_valid_plus_blank_conflict_not_accepted(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id=""),
            ),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_valid_plus_whitespace_conflict(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="   "),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
            ),
        )
        assert status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert release_id == ""

    def test_unrelated_invalid_candidate_ignored(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (ReleaseEditionCandidate(release_id="rel-y", release_group_id=""),),
        )
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == ""

    def test_invalid_current_group_argument_value_error(self):
        with pytest.raises(ValueError):
            resolve_release_hint_for_group("", "rel-x", ())

    def test_invalid_hint_argument_value_error(self):
        with pytest.raises(ValueError):
            resolve_release_hint_for_group("rg-a", "   ", ())

    def test_valid_duplicate_mapping_still_works(self):
        status, release_id = resolve_release_hint_for_group(
            "rg-a",
            "rel-x",
            (
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
                ReleaseEditionCandidate(release_id="rel-x", release_group_id="rg-a"),
            ),
        )
        assert status is IdentityResolutionStatus.RESOLVED
        assert release_id == "rel-x"


# ---------------------------------------------------------------------------
# GROUP B — PERSISTENT IDENTITY RUNTIME TYPE SAFETY
# ---------------------------------------------------------------------------


class TestPersistentIdentityTypeSafety:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("local_artist_key", 123),
            ("local_artist_key", None),
            ("external_artist_id", 123),
            ("external_artist_id", None),
            ("external_artist_id", b"mb-a"),
            ("external_artist_id", "   "),
            ("external_artist_id", " mb-a "),
            ("resolved_at", 123),
        ],
    )
    def test_artist_invalid_field_rejected(self, field, value):
        kwargs = {"local_artist_key": "k", "external_artist_id": "mb-a"}
        kwargs[field] = value
        with pytest.raises(ValueError):
            ArtistExternalIdentity(**kwargs)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("local_album_key", 123),
            ("release_group_id", 123),
            ("release_group_id", None),
            ("release_group_id", b"rg-a"),
            ("release_group_id", "   "),
            ("release_group_id", " rg-a "),
            ("release_id", 123),
            ("release_id", None),
            ("release_id", "   "),
            ("release_id", " rel-a "),
            ("resolved_at", []),
        ],
    )
    def test_album_invalid_field_rejected(self, field, value):
        kwargs = {"local_album_key": "k", "release_group_id": "rg-a"}
        kwargs[field] = value
        with pytest.raises(ValueError):
            AlbumExternalIdentity(**kwargs)

    def test_album_empty_release_id_valid(self):
        identity = AlbumExternalIdentity(
            local_album_key="k", release_group_id="rg-a", release_id=""
        )
        assert identity.release_id == ""


# ---------------------------------------------------------------------------
# GROUP C — SQLITE IDENTITY CORRUPTION (WRONG RUNTIME TYPES)
# ---------------------------------------------------------------------------


class TestSqliteIdentityCorruption:
    """R3.2.1: wrong runtime types in identity rows are corruption.

    NOTE: the canonical V3 schema declares TEXT affinity for every
    identity column, so raw SQLite inserts are COERCED to str by SQLite
    affinity before storage — the database layer cannot smuggle wrong
    runtime types under a validated canonical schema. The corruption
    boundary therefore lives at the row DECODER (unit seam), which must
    translate every wrong type into EnrichmentStorageError — never None,
    never AttributeError."""

    def test_artist_external_id_wrong_type(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._artist_identity_from_row(
                ("bad-key", 123, "RESOLVED", "AUTO", "when")
            )

    def test_artist_resolved_at_wrong_type(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._artist_identity_from_row(
                ("bad-key", "mb-x", "RESOLVED", "AUTO", 123)
            )

    def test_album_rg_wrong_type(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._album_identity_from_row(
                ("bad-key", 123, "", "RESOLVED", "AUTO", "when")
            )

    def test_album_release_wrong_type(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._album_identity_from_row(
                ("bad-key", "rg-a", 123, "RESOLVED", "AUTO", "when")
            )

    def test_album_resolved_at_wrong_type(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._album_identity_from_row(
                ("bad-key", "rg-a", "", "RESOLVED", "AUTO", 123)
            )

    def test_none_of_the_above_leaks_attribute_error(self):
        with pytest.raises(EnrichmentStorageError):
            SqliteEnrichmentRepository._artist_identity_from_row(
                ("bad-key", None, "RESOLVED", "AUTO", "when")
            )


# ---------------------------------------------------------------------------
# GROUP D — V2 SEMANTIC SOURCE
# ---------------------------------------------------------------------------


class TestV2SemanticSource:
    def test_v2_artist_resolved_at_int_rejected(self, tmp_path):
        # BLOB-affinity resolved_at column (same NAME, no TEXT affinity)
        # stores the int AS an int — the V2 semantic validator must
        # reject it. (Canonical TEXT columns coerce inserts to str.)
        db_path = tmp_path / "enrichment.db"
        _exec(
            db_path,
            (
                *V1_TABLES_SQL,
                "CREATE TABLE artist_identity ("
                "local_artist_key TEXT PRIMARY KEY,"
                "external_artist_id TEXT NOT NULL,"
                "status TEXT NOT NULL,"
                "match_method TEXT NOT NULL,"
                "manually_confirmed INTEGER NOT NULL,"
                "resolved_at NOT NULL)",
                "CREATE TABLE album_identity ("
                "local_album_key TEXT PRIMARY KEY,"
                "release_group_id TEXT NOT NULL,"
                "release_id TEXT NOT NULL,"
                "status TEXT NOT NULL,"
                "match_method TEXT NOT NULL,"
                "manually_confirmed INTEGER NOT NULL,"
                "resolved_at TEXT NOT NULL)",
                (
                    "INSERT INTO enrichment_meta VALUES(?, ?)",
                    ("enrichment_schema_version", "2"),
                ),
            ),
        )
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?, ?)",
                ("the cure", "mb-cure", "RESOLVED", "MANUAL", 1, 123),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"

    def test_v2_album_resolved_at_int_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _exec(
            db_path,
            (
                *V1_TABLES_SQL,
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
                "resolved_at NOT NULL)",
                (
                    "INSERT INTO enrichment_meta VALUES(?, ?)",
                    ("enrichment_schema_version", "2"),
                ),
            ),
        )
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO album_identity VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("album-a", "rg-a", "", "RESOLVED", "AUTO", 0, 123),
            )
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"

    @pytest.mark.parametrize("confirmed", [0, 1])
    def test_v2_confirmed_zero_one_valid(self, tmp_path, confirmed):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(
            db_path,
            artist_row=("the cure", "mb-cure", "RESOLVED", "MANUAL", confirmed, "when"),
        )
        repo = SqliteEnrichmentRepository(db_path)
        identity = repo.load_artist_identity("the cure")
        assert identity is not None
        # MatchMethod remains the authority; the boolean is dropped.
        assert identity.match_method is MatchMethod.MANUAL

    @pytest.mark.parametrize("confirmed", [2, -1])
    def test_v2_confirmed_out_of_range_rejected(self, tmp_path, confirmed):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(
            db_path,
            artist_row=("the cure", "mb-cure", "RESOLVED", "MANUAL", confirmed, "when"),
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"

    def test_v2_confirmed_text_rejected(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(
            db_path,
            artist_row=("the cure", "mb-cure", "RESOLVED", "MANUAL", "banana", "when"),
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert _version_row(db_path) == "2"


# ---------------------------------------------------------------------------
# GROUP E — ALBUM KNOWLEDGE AUTHORITY
# ---------------------------------------------------------------------------


class TestAlbumKnowledgeAuthority:
    def test_auto_same_rg_preserves_knowledge(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        knowledge.save_album_profile(
            FakeAlbumProvider().fetch_profile("album-a", "rg-x")
        )
        assert knowledge.load_album_profile("album-a") is not None
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-x"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(album_evidence())
        assert outcome.request is not None
        # Same identity refresh: knowledge PRESERVED.
        assert knowledge.load_album_profile("album-a") is not None

    def test_auto_changed_rg_deletes_knowledge(self):
        identity_repo = InMemoryIdentityRepository()
        identity_repo.save_album_identity(
            AlbumExternalIdentity(
                local_album_key="album-a",
                release_group_id="rg-x",
                match_method=MatchMethod.AUTO,
            )
        )
        knowledge = RecordingKnowledgeRepository()
        knowledge.save_album_profile(
            FakeAlbumProvider().fetch_profile("album-a", "rg-x")
        )
        resolver = ScriptedResolver()
        resolver.group_batches.append((auto_group("rg-y"),))
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(album_evidence())
        assert outcome.request.external_entity_id == "rg-y"
        assert knowledge.load_album_profile("album-a") is None
        assert identity_repo.load_album_identity("album-a").release_group_id == "rg-y"

    def test_embedded_same_edition_preserves_knowledge(self):
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
        knowledge.save_album_profile(
            FakeAlbumProvider().fetch_profile("album-a", "rg-x", "rel-a")
        )
        resolver = ScriptedResolver()
        resolver.edition_batches.append(
            (ReleaseEditionCandidate(release_id="rel-a", release_group_id="rg-x"),)
        )
        service = make_service(
            resolver=resolver, repository=knowledge, identity_repository=identity_repo
        )
        outcome = service.request_album_enrichment(
            album_evidence(release_ids=("rel-a",))
        )
        assert outcome.request.external_variant_id == "rel-a"
        assert knowledge.load_album_profile("album-a") is not None
        identity = identity_repo.load_album_identity("album-a")
        assert identity.match_method is MatchMethod.EMBEDDED_HINT

    def test_embedded_changed_edition_deletes_knowledge_and_stales(self):
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
            album_evidence(release_ids=("rel-b",))
        )
        assert outcome.request.external_variant_id == "rel-b"
        assert knowledge.load_album_profile("album-a") is None
        assert identity_repo.load_album_identity("album-a").release_id == "rel-b"

    def test_same_service_ledger_invalidation_after_revocation(self):
        """Same-service proof: the request was registered AND invalidated
        by the revocation in ONE ledger — the late result is STALE."""
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
        first = service.request_album_enrichment(album_evidence())
        assert first.request is not None
        # Direct conflicting hints revoke the AUTO mapping via the SAME
        # service (same ledger).
        conflicting_outcome = service.request_album_enrichment(
            album_evidence(rg_ids=("rg-x", "rg-y"))
        )
        assert conflicting_outcome.request is None
        assert identity_repo.load_album_identity("album-a") is None
        profile = service._album_provider.fetch_profile("album-a", "rg-x")
        assert (
            service.deliver_album_profile(first.request, profile)
            is DeliveryVerdict.STALE
        )


# ---------------------------------------------------------------------------
# GROUP F — TRANSACTIONAL NEW DATABASE INITIALIZATION
# ---------------------------------------------------------------------------


class TestNewDatabaseTransaction:
    def _tables(self, db_path: Path) -> list:
        conn = sqlite3.connect(str(db_path))
        try:
            return conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            conn.close()

    def test_fresh_canonical_initialization(self, tmp_path):
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

    def test_injected_validation_failure_commits_no_schema(self, tmp_path, monkeypatch):
        db_path = tmp_path / "enrichment.db"

        def fail_validation(self, conn):
            raise EnrichmentSchemaError("injected init validation failure")

        monkeypatch.setattr(
            SqliteEnrichmentRepository, "_validate_current_schema", fail_validation
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        # No partial enrichment schema committed.
        assert self._tables(db_path) == []

    def test_retry_after_failure_succeeds(self, tmp_path, monkeypatch):
        db_path = tmp_path / "enrichment.db"
        original = SqliteEnrichmentRepository._validate_current_schema
        state = {"fail": True}

        def fail_once(self, conn):
            if state["fail"]:
                state["fail"] = False
                raise EnrichmentSchemaError("injected once")
            return original(conn)

        monkeypatch.setattr(
            SqliteEnrichmentRepository, "_validate_current_schema", fail_once
        )
        with pytest.raises(EnrichmentSchemaError):
            SqliteEnrichmentRepository(db_path)
        assert self._tables(db_path) == []
        repo = SqliteEnrichmentRepository(db_path)
        assert repo.version() == 3
