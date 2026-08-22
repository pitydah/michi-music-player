"""M6.9A-R2 — REAL historical migration tests (literal fixtures).

The v1 fixtures below are literal JSON matching the ACTUAL M6.9A model
(commit 1556e66: profiles carried ``source`` + ``generation``) and are
NEVER generated with the current encoder — they must keep proving real
v1 compatibility even if today's models change. The v2 fixture is the
R1 schema (identity tables with the legacy ``manually_confirmed``
column). Schema 3 is the R2 shape (no redundant boolean).

Migration contract:
- v1 knowledge rows are TRANSFORMED (source -> provenance.provider,
  generation dropped, release-level facts without a release identity
  dropped — never invented); malformed rows are deleted deterministically;
- v2 identity rows are normalized into the v3 shape (manual authority =
  MatchMethod.MANUAL only), knowledge preserved;
- manual mappings survive every migration;
- newer schemas fail closed;
- the canonical library is never touched.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from michi.domain.enrichment import MatchMethod
from michi.infrastructure.enrichment_repository import (
    CURRENT_ENRICHMENT_SCHEMA,
    EnrichmentSchemaError,
    SqliteEnrichmentRepository,
)

# ---------------------------------------------------------------------------
# LITERAL HISTORICAL FIXTURES (never generated from current models)
# ---------------------------------------------------------------------------

V1_ARTIST_PAYLOAD = {
    "local_artist_key": "the cure",
    "external_artist_id": "69ee3720-a7cb-4402-b48d-a02c366f2bcf",
    "biography": "English rock band formed in Crawley in 1976.",
    "external_genres": ["Post-Punk", "Gothic Rock"],
    "begin_year": 1976,
    "end_year": 0,
    "artwork_asset_id": "asset-cure",
    "source": "musicbrainz",
    "generation": 2,
}

V1_ALBUM_PAYLOAD = {
    "local_album_key": "12::disintegration::the cure",
    "release_group_id": "rg-disintegration",
    "release_id": "",
    "external_genres": ["Gothic Rock"],
    "first_release_year": 1989,
    "release_year": 1989,
    "label": "Fiction",
    "artwork_asset_id": "",
    "source": "musicbrainz",
    "generation": 3,
}

V1_MALFORMED_PAYLOAD = '{"local_artist_key": "broken", "external_artist_id": 42}'

_PROVENANCE = {
    "provider": "musicbrainz",
    "external_entity_id": "",
    "source_url": "",
    "retrieved_at": "",
    "language": "",
    "license": "",
    "license_url": "",
    "attribution": "",
}

V2_ARTIST_KNOWLEDGE_PAYLOAD = {
    "local_artist_key": "the cure",
    "external_artist_id": "mb-xyz",
    "biography": "English rock band.",
    "external_genres": ["Post-Punk"],
    "begin_year": 1976,
    "end_year": 0,
    "artwork_asset_id": "",
    "provenance": _PROVENANCE,
    "biography_provenance": {**_PROVENANCE, "provider": "wikipedia"},
}

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


def _create_db(db_path: Path, statements: tuple[str, ...], rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        for statement in statements:
            conn.execute(statement)
        for row in rows:
            conn.execute(row[0], row[1])
        conn.commit()
    finally:
        conn.close()


def _create_v1_db(db_path: Path) -> None:
    _create_db(
        db_path,
        V1_TABLES_SQL,
        [
            (
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "1"),
            ),
            (
                "INSERT INTO artist_knowledge VALUES(?, ?)",
                ("the cure", json.dumps(V1_ARTIST_PAYLOAD)),
            ),
            (
                "INSERT INTO artist_knowledge VALUES(?, ?)",
                ("broken", V1_MALFORMED_PAYLOAD),
            ),
            (
                "INSERT INTO album_knowledge VALUES(?, ?)",
                ("12::disintegration::the cure", json.dumps(V1_ALBUM_PAYLOAD)),
            ),
        ],
    )


def _create_v2_db(db_path: Path) -> None:
    _create_db(
        db_path,
        (*V1_TABLES_SQL, *V2_IDENTITY_SQL),
        [
            (
                "INSERT INTO enrichment_meta VALUES(?, ?)",
                ("enrichment_schema_version", "2"),
            ),
            (
                "INSERT INTO artist_knowledge VALUES(?, ?)",
                ("the cure", json.dumps(V2_ARTIST_KNOWLEDGE_PAYLOAD)),
            ),
            (
                "INSERT INTO artist_identity VALUES(?, ?, ?, ?, ?, ?)",
                ("the cure", "mb-xyz", "RESOLVED", "MANUAL", 1, "when"),
            ),
            (
                "INSERT INTO album_identity VALUES(?, ?, ?, ?, ?, ?, ?)",
                ("album-key", "rg-x", "", "RESOLVED", "AUTO", 0, "when"),
            ),
        ],
    )


def _columns(conn, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


class TestRealV1Migration:
    def test_real_v1_artist_migration(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v1_db(db_path)
        repo = SqliteEnrichmentRepository(db_path)
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

        profile = repo.load_artist_profile("the cure")
        assert profile is not None
        assert profile.external_artist_id == V1_ARTIST_PAYLOAD["external_artist_id"]
        assert profile.biography == V1_ARTIST_PAYLOAD["biography"]
        assert profile.external_genres == ("Post-Punk", "Gothic Rock")
        # source translated truthfully; nothing fabricated.
        assert profile.provenance.provider == "musicbrainz"
        assert profile.provenance.source_url == ""
        assert profile.provenance.license == ""
        # generation is NOT knowledge: absent from the migrated model.
        assert "generation" not in profile.__dataclass_fields__
        # The malformed row was deleted deterministically.
        assert repo.load_artist_profile("broken") is None
        assert repo.load_artist_profiles() == (profile,)

    def test_real_v1_album_migration(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v1_db(db_path)
        repo = SqliteEnrichmentRepository(db_path)

        profile = repo.load_album_profile("12::disintegration::the cure")
        assert profile is not None
        assert profile.release_group_id == "rg-disintegration"
        # External first release date remains external (never a local fact).
        assert profile.first_release_year == 1989
        # Release-level facts without a release identity were DROPPED —
        # no invented release_id.
        assert profile.release_id == ""
        assert profile.release_year == 0
        assert profile.label == ""
        assert profile.provenance.provider == "musicbrainz"
        assert "generation" not in profile.__dataclass_fields__


class TestV2ToV3Migration:
    def test_v2_to_v3_preserves_identities_and_knowledge(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v2_db(db_path)
        repo = SqliteEnrichmentRepository(db_path)
        assert repo.version() == CURRENT_ENRICHMENT_SCHEMA == 3

        # Manual mapping survived; MANUAL authority is MatchMethod only.
        identity = repo.load_artist_identity("the cure")
        assert identity is not None
        assert identity.external_artist_id == "mb-xyz"
        assert identity.match_method is MatchMethod.MANUAL
        assert "manually_confirmed" not in identity.__dataclass_fields__

        album_identity = repo.load_album_identity("album-key")
        assert album_identity is not None
        assert album_identity.match_method is MatchMethod.AUTO

        # Knowledge preserved (v2 shape == v3 shape).
        profile = repo.load_artist_profile("the cure")
        assert profile is not None
        assert profile.external_artist_id == "mb-xyz"
        assert profile.biography_provenance.provider == "wikipedia"

        # The redundant column is physically gone from schema 3.
        conn = sqlite3.connect(str(db_path))
        try:
            assert _columns(conn, "artist_identity") == [
                "local_artist_key",
                "external_artist_id",
                "status",
                "match_method",
                "resolved_at",
            ]
        finally:
            conn.close()

    def test_migration_chain_v1_v2_v3(self, tmp_path):
        """1 -> 3 and 2 -> 3 both converge on the current schema without
        losing identity or knowledge."""
        db_path = tmp_path / "enrichment.db"
        _create_v1_db(db_path)
        repo_v1 = SqliteEnrichmentRepository(db_path)
        assert repo_v1.version() == 3
        repo_v1.save_artist_identity(_manual_identity())
        assert (
            repo_v1.load_artist_identity("the cure").match_method is MatchMethod.MANUAL
        )

        v2_db = tmp_path / "enrichment-v2.db"
        _create_v2_db(v2_db)
        repo_v2 = SqliteEnrichmentRepository(v2_db)
        assert repo_v2.version() == 3
        assert repo_v2.load_artist_identity("the cure") is not None

    def test_newer_schema_fails_closed(self, tmp_path):
        db_path = tmp_path / "enrichment.db"
        _create_v1_db(db_path)
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


def _manual_identity():
    from michi.domain.enrichment import (
        ArtistExternalIdentity,
        IdentityStatus,
    )

    return ArtistExternalIdentity(
        local_artist_key="the cure",
        external_artist_id="mb-manual",
        status=IdentityStatus.RESOLVED,
        match_method=MatchMethod.MANUAL,
        resolved_at="when",
    )
