"""SQLite enrichment repository (M6.9A-R2) — enrichment.db EXCLUSIVELY.

M6.9A LIBRARY INDEX FIREWALL: enrichment owns its own database file and
its own tables. The canonical ``library_index`` / ``library_meta`` tables
are NEVER touched — no shared schema, no shared version key, no
cross-writes. External knowledge can never enter the library index.

ONE schema owner (this class implements BOTH ``KnowledgeRepositoryPort``
and ``IdentityRepositoryPort`` — identity authority and downloaded
knowledge are different TABLES, same database).

R2 SCHEMA 3 + REAL MIGRATION CHAIN:

- v1 (M6.9A): knowledge profiles carry ``source`` + ``generation``
  (historical shape, decoders below) and NO identity tables.
- v2 (R1): identity tables (with the legacy ``manually_confirmed``
  column) + provenance-shaped knowledge.
- v3 (R2): identity tables WITHOUT the redundant boolean; MANUAL
  authority is MatchMethod only.

Migrations are TRANSACTIONAL and perform REAL data transformation:
v1 knowledge rows are rewritten into the current shape (``source`` ->
provenance.provider; ``generation`` DROPPED — async lifecycle is not
knowledge; release-level facts without a release identity are dropped —
never invented). Malformed rows are skipped/deleted deterministically
(enrichment is a cache; identity authority and the canonical library are
never harmed). v2 identity rows are normalized into the v3 shape.
Newer schemas fail closed.
"""

import contextlib
import json
import logging
import sqlite3
from pathlib import Path

from michi.application.enrichment_ports import (
    EnrichmentStorageError,
    IdentityRepositoryPort,
    KnowledgeRepositoryPort,
)
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumKnowledgeProfile,
    ArtistExternalIdentity,
    ArtistKnowledgeProfile,
    IdentityStatus,
    KnowledgeProvenance,
    MatchMethod,
    decode_album_profile,
    decode_artist_profile,
    encode_album_profile,
    encode_artist_profile,
)

logger = logging.getLogger(__name__)

CURRENT_ENRICHMENT_SCHEMA = 3
_VERSION_KEY = "enrichment_schema_version"


class EnrichmentSchemaError(RuntimeError):
    """The enrichment database violates the schema/version CONTRACT.

    Raised for: a future (newer) schema version, malformed/zero/negative
    version metadata, missing required tables, an invalid current shape
    (including a mislabeled V2 identity shape inside a V3 database),
    corrupt migration sources (partial V2, unexpected V1 identity
    tables) and missing version rows. Schema violations NEVER mutate
    the database and are distinct from operational storage failures
    (``EnrichmentStorageError``)."""


# ---------------------------------------------------------------------------
# HISTORICAL V1 CODECS (M6.9A, commit 1556e66) — literal field sets.
# NEVER generated with the current encoder: these must survive model
# changes forever so real v1 databases keep migrating correctly.
# ---------------------------------------------------------------------------

_V1_ARTIST_STR_FIELDS = {
    "local_artist_key",
    "external_artist_id",
    "biography",
    "artwork_asset_id",
    "source",
}
_V1_ARTIST_FIELDS = _V1_ARTIST_STR_FIELDS | {
    "external_genres",
    "begin_year",
    "end_year",
    "generation",
}
_V1_ALBUM_STR_FIELDS = {
    "local_album_key",
    "release_group_id",
    "release_id",
    "label",
    "artwork_asset_id",
    "source",
}
_V1_ALBUM_FIELDS = _V1_ALBUM_STR_FIELDS | {
    "external_genres",
    "first_release_year",
    "release_year",
    "generation",
}


def _decode_v1_payload(
    raw: str, str_fields: set[str], all_fields: set[str]
) -> dict | None:
    """Strict decode of a historical v1 profile payload."""
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    out: dict = {}
    for name in all_fields:
        if name not in payload:
            return None  # missing historical field
        value = payload[name]
        if name in str_fields:
            if not isinstance(value, str):
                return None
        elif name == "external_genres":
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                return None
        else:  # int fields (begin_year/end_year/generation/...)
            if isinstance(value, bool) or not isinstance(value, int):
                return None
        out[name] = value
    return out


def _transform_v1_artist(payload: dict) -> str | None:
    """v1 artist -> current shape. ``source`` -> provenance.provider;
    ``generation`` DROPPED (async lifecycle is not knowledge); nothing
    else is fabricated.

    R3 BIOGRAPHY PROVENANCE: when the historical profile carries a
    non-empty biography AND a non-empty source, that source context
    truthfully applies to the biography as well —
    ``biography_provenance.provider`` is preserved. Unsupported fields
    (source_url / language / license / ...) stay unknown."""
    source = payload["source"]
    biography = payload["biography"]
    profile = ArtistKnowledgeProfile(
        local_artist_key=payload["local_artist_key"],
        external_artist_id=payload["external_artist_id"],
        biography=biography,
        external_genres=tuple(payload["external_genres"]),
        begin_year=payload["begin_year"],
        end_year=payload["end_year"],
        artwork_asset_id=payload["artwork_asset_id"],
        provenance=KnowledgeProvenance(provider=source),
        biography_provenance=(
            KnowledgeProvenance(provider=source)
            if biography and source
            else KnowledgeProvenance()
        ),
    )
    return encode_artist_profile(profile)


def _transform_v1_album(payload: dict) -> str | None:
    """v1 album -> current shape. ``source`` -> provenance.provider;
    ``generation`` DROPPED; release-level facts (release_year/label)
    without a release identity are DROPPED — never invent a release_id."""
    release_id = payload["release_id"]
    profile = AlbumKnowledgeProfile(
        local_album_key=payload["local_album_key"],
        release_group_id=payload["release_group_id"],
        release_id=release_id,
        external_genres=tuple(payload["external_genres"]),
        first_release_year=payload["first_release_year"],
        release_year=payload["release_year"] if release_id else 0,
        label=payload["label"] if release_id else "",
        artwork_asset_id=payload["artwork_asset_id"],
        provenance=KnowledgeProvenance(provider=payload["source"]),
    )
    return encode_album_profile(profile)


class SqliteEnrichmentRepository(KnowledgeRepositoryPort, IdentityRepositoryPort):
    """Single schema authority for enrichment.db.

    R3 TRUTHFUL PERSISTENCE: identity AND knowledge reads/writes raise
    ``EnrichmentStorageError`` on operational failure (never a silent
    fake success); malformed identity authority rows raise as
    corruption (never degrade to 'no identity'). Malformed knowledge
    CACHE rows degrade to None (rebuildable cache, logged). Schema
    contract violations raise ``EnrichmentSchemaError`` without
    mutating the database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(str(self._db_path), isolation_level=None)

    # -- schema (single owner) ----------------------------------------------

    @staticmethod
    def _create_knowledge_tables(conn) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS artist_knowledge ("
            "local_artist_key TEXT PRIMARY KEY,"
            "profile TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS album_knowledge ("
            "local_album_key TEXT PRIMARY KEY,"
            "profile TEXT NOT NULL)"
        )

    @staticmethod
    def _create_meta_table(conn) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS enrichment_meta ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )

    @staticmethod
    def _create_identity_tables_v3(conn) -> None:
        """Schema 3 identity tables: NO redundant manually_confirmed."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS artist_identity ("
            "local_artist_key TEXT PRIMARY KEY,"
            "external_artist_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS album_identity ("
            "local_album_key TEXT PRIMARY KEY,"
            "release_group_id TEXT NOT NULL,"
            "release_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )

    @staticmethod
    def _create_identity_tables_v2(conn) -> None:
        """Schema 2 identity tables (R1 shape, legacy boolean column) —
        only used to build REAL v2 migration fixtures in tests."""
        conn.execute(
            "CREATE TABLE artist_identity ("
            "local_artist_key TEXT PRIMARY KEY,"
            "external_artist_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "manually_confirmed INTEGER NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE album_identity ("
            "local_album_key TEXT PRIMARY KEY,"
            "release_group_id TEXT NOT NULL,"
            "release_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "manually_confirmed INTEGER NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )

    def _ensure_schema(self) -> None:
        """R3 NON-MUTATING SCHEMA DISCOVERY.

        The database state is determined BEFORE anything is created:
        - brand-new empty database -> initialize current schema;
        - enrichment tables WITHOUT version metadata -> corrupt, fail;
        - v1/v2 -> transactional migration;
        - v3 -> VALIDATE the structural shape (no silent repair);
        - future (> current), non-numeric, negative or zero version ->
          EnrichmentSchemaError WITHOUT touching the database.
        """
        conn = self._connect()
        try:
            meta = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='enrichment_meta'"
            ).fetchone()
            if meta is None:
                existing = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('artist_knowledge', 'album_knowledge', "
                    "'artist_identity', 'album_identity')"
                ).fetchall()
                if existing:
                    raise EnrichmentSchemaError(
                        "enrichment tables exist without version metadata"
                    )
                self._create_knowledge_tables(conn)
                self._create_meta_table(conn)
                self._create_identity_tables_v3(conn)
                conn.execute(
                    "INSERT INTO enrichment_meta(key, value) VALUES(?, ?)",
                    (_VERSION_KEY, str(CURRENT_ENRICHMENT_SCHEMA)),
                )
                return
            row = conn.execute(
                "SELECT value FROM enrichment_meta WHERE key = ?", (_VERSION_KEY,)
            ).fetchone()
            if row is None:
                raise EnrichmentSchemaError(
                    "enrichment_meta exists without a version row"
                )
            raw = row[0]
            if not str(raw).isdigit() or int(raw) <= 0:
                # Non-numeric, empty, negative or zero: malformed metadata
                # is NEVER rewritten and never upgraded.
                raise EnrichmentSchemaError(
                    f"invalid enrichment schema version: {raw!r}"
                )
            version = int(raw)
            if version > CURRENT_ENRICHMENT_SCHEMA:
                raise EnrichmentSchemaError(
                    f"enrichment schema version {version} is newer "
                    f"than supported {CURRENT_ENRICHMENT_SCHEMA}"
                )
            if version in (1, 2):
                # R3.2: the SOURCE schema is validated (structure for
                # both, authority-row SEMANTICS for V2) BEFORE the
                # transaction starts.
                self._validate_knowledge_tables(conn)
                if version == 1:
                    # R3.1: historical V1 has NO identity tables — if any
                    # exists the database is inconsistent and never guessed.
                    self._require_identity_tables_absent(conn)
                else:
                    # R3.1/R3.2: V2 requires BOTH identity tables in the
                    # exact V2 shape (including the legacy boolean) AND
                    # semantically valid authority rows.
                    self._validate_v2_identity_shape(conn)
                    self._validate_v2_identity_rows(conn)
                conn.execute("BEGIN")
                try:
                    if version == 1:
                        self._migrate_v1_knowledge(conn)
                        self._create_identity_tables_v3(conn)
                    else:
                        self._migrate_v2_identities(conn)
                    conn.execute(
                        "UPDATE enrichment_meta SET value = ? WHERE key = ?",
                        (str(CURRENT_ENRICHMENT_SCHEMA), _VERSION_KEY),
                    )
                    # R3.2 MIGRATION COMMIT GATE: a migration succeeds
                    # ONLY if the resulting database is a valid CURRENT
                    # schema — validated INSIDE the transaction, BEFORE
                    # COMMIT (any failure rolls the source back).
                    self._validate_current_schema(conn)
                    conn.execute("COMMIT")
                except Exception:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
                return
            # version == CURRENT: validate, NEVER auto-repair.
            self._validate_current_schema(conn)
        except sqlite3.Error as exc:
            raise EnrichmentSchemaError(
                f"enrichment schema bootstrap failed: {exc}"
            ) from exc
        finally:
            conn.close()

    @staticmethod
    def _validate_current_schema(conn) -> None:
        """R3/R3.1/R3.2 fail-closed current-schema validation.

        Identity authority shape is EXACT — a V3 database whose identity
        tables still carry the legacy V2 ``manually_confirmed`` column is
        a mislabeled V2 and never accepted. R3.2: validation covers the
        FULL canonical PRAGMA signature (column name, declared type,
        NOT NULL contract, primary-key role) computed from the CURRENT
        canonical DDL itself — never hand-guessed, and robust to SQLite
        rowid-table PK quirks. Identity tables are USER AUTHORITY and
        are never silently recreated empty."""
        for table in (
            "artist_identity",
            "album_identity",
            "artist_knowledge",
            "album_knowledge",
            "enrichment_meta",
        ):
            expected = SqliteEnrichmentRepository._canonical_signature(table)
            actual = conn.execute(f"PRAGMA table_info({table})").fetchall()
            if not actual:
                raise EnrichmentSchemaError(f"missing table {table}")
            actual_signature = [
                (row[1], str(row[2]), int(row[3]), int(row[5])) for row in actual
            ]
            if actual_signature != expected:
                raise EnrichmentSchemaError(
                    f"table {table} invalid canonical shape: "
                    f"{actual_signature} != {expected}"
                )

    @staticmethod
    def _canonical_signature(table: str) -> list[tuple[str, str, int, int]]:
        """R3.2: PRAGMA table_info signature of the CANONICAL current
        DDL — built fresh in-memory with the exact DDL helpers used for
        brand-new databases. The DDL itself is the contract, so SQLite's
        real PK/NOT NULL reporting (including rowid quirks) is compared
        truthfully instead of invented."""
        conn = sqlite3.connect(":memory:")
        try:
            SqliteEnrichmentRepository._create_knowledge_tables(conn)
            SqliteEnrichmentRepository._create_identity_tables_v3(conn)
            SqliteEnrichmentRepository._create_meta_table(conn)
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return [(row[1], str(row[2]), int(row[3]), int(row[5])) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _table_columns(conn, table: str) -> list[str] | None:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [row[1] for row in info] if info else None

    @staticmethod
    def _validate_knowledge_tables(conn) -> None:
        """R3.2: migration sources must contain BOTH knowledge tables
        with the required columns (a partial source is corrupt)."""
        for table, key_column in (
            ("artist_knowledge", "local_artist_key"),
            ("album_knowledge", "local_album_key"),
        ):
            actual = SqliteEnrichmentRepository._table_columns(conn, table)
            if actual is None or not {"profile", key_column}.issubset(set(actual)):
                raise EnrichmentSchemaError(
                    f"migration source missing/invalid {table}: {actual}"
                )

    @staticmethod
    def _validate_v2_identity_rows(conn) -> None:
        """R3.2 SEMANTIC V2 VALIDATION: every V2 identity authority row
        must decode through the CURRENT identity constructors (non-empty
        keys/ids, RESOLVED-only status, valid MatchMethod, string
        resolved_at). Malformed authority rows FAIL the migration and
        roll back — never skipped, deleted, or normalized. The legacy
        ``manually_confirmed`` column is IGNORED for V3 authority
        (MatchMethod is the authority since R2)."""
        for table, columns in (
            (
                "artist_identity",
                "local_artist_key, external_artist_id, status, "
                "match_method, manually_confirmed, resolved_at",
            ),
            (
                "album_identity",
                "local_album_key, release_group_id, release_id, "
                "status, match_method, manually_confirmed, resolved_at",
            ),
        ):
            rows = conn.execute(f"SELECT {columns} FROM {table}").fetchall()
            for row in rows:
                try:
                    if table == "artist_identity":
                        SqliteEnrichmentRepository._artist_identity_from_row(
                            (row[0], row[1], row[2], row[3], row[5])
                        )
                    else:
                        SqliteEnrichmentRepository._album_identity_from_row(
                            (row[0], row[1], row[2], row[3], row[4], row[6])
                        )
                except EnrichmentStorageError as exc:
                    raise EnrichmentSchemaError(
                        f"malformed v2 {table} row {row[0]!r}: {exc}"
                    ) from exc

    @staticmethod
    def _require_identity_tables_absent(conn) -> None:
        for table in ("artist_identity", "album_identity"):
            if SqliteEnrichmentRepository._table_columns(conn, table) is not None:
                raise EnrichmentSchemaError(
                    f"v1 database unexpectedly contains {table}"
                )

    @staticmethod
    def _validate_v2_identity_shape(conn) -> None:
        """R3.1: a V2 database MUST contain BOTH identity tables with
        the exact V2 column shape (including manually_confirmed). A
        partial or wrong-shape V2 is corrupt and never migrated."""
        expected = {
            "artist_identity": (
                "local_artist_key",
                "external_artist_id",
                "status",
                "match_method",
                "manually_confirmed",
                "resolved_at",
            ),
            "album_identity": (
                "local_album_key",
                "release_group_id",
                "release_id",
                "status",
                "match_method",
                "manually_confirmed",
                "resolved_at",
            ),
        }
        for table, columns in expected.items():
            actual = SqliteEnrichmentRepository._table_columns(conn, table)
            if actual != list(columns):
                raise EnrichmentSchemaError(
                    f"v2 identity table {table} invalid shape: {actual}"
                )

    def _migrate_v1_knowledge(self, conn) -> None:
        """REAL v1 data transformation (R2): rewrite every valid v1
        profile into the current shape; malformed rows are DELETED
        (deterministic fail-safe — enrichment is a cache; the identity
        authority and the canonical library are never touched)."""
        for table, key_column, decoder_fields, transform in (
            (
                "artist_knowledge",
                "local_artist_key",
                (_V1_ARTIST_STR_FIELDS, _V1_ARTIST_FIELDS),
                _transform_v1_artist,
            ),
            (
                "album_knowledge",
                "local_album_key",
                (_V1_ALBUM_STR_FIELDS, _V1_ALBUM_FIELDS),
                _transform_v1_album,
            ),
        ):
            rows = conn.execute(f"SELECT {key_column}, profile FROM {table}").fetchall()
            for key, raw_profile in rows:
                payload = _decode_v1_payload(raw_profile, *decoder_fields)
                if payload is None:
                    conn.execute(f"DELETE FROM {table} WHERE {key_column} = ?", (key,))
                    continue
                transformed = transform(payload)
                if transformed is None:
                    conn.execute(f"DELETE FROM {table} WHERE {key_column} = ?", (key,))
                    continue
                conn.execute(
                    f"UPDATE {table} SET profile = ? WHERE {key_column} = ?",
                    (transformed, key),
                )

    @staticmethod
    def _migrate_v2_identities(conn) -> None:
        """v2 -> v3: rebuild identity tables WITHOUT the legacy boolean
        (MANUAL authority = MatchMethod only). Rows are preserved. A v1
        database has NO identity tables: the v3 shape is created fresh."""
        exists = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='artist_identity'"
        ).fetchone()
        if exists is None:
            SqliteEnrichmentRepository._create_identity_tables_v3(conn)
            return
        for table, columns in (
            (
                "artist_identity",
                "local_artist_key, external_artist_id, status, "
                "match_method, resolved_at",
            ),
            (
                "album_identity",
                "local_album_key, release_group_id, release_id, "
                "status, match_method, resolved_at",
            ),
        ):
            conn.execute(f"DROP TABLE IF EXISTS {table}_v3")
            conn.execute(
                f"CREATE TABLE {table}_v3 ("
                + (
                    "local_artist_key TEXT PRIMARY KEY,"
                    "external_artist_id TEXT NOT NULL,"
                    if table == "artist_identity"
                    else "local_album_key TEXT PRIMARY KEY,"
                    "release_group_id TEXT NOT NULL,"
                    "release_id TEXT NOT NULL,"
                )
                + "status TEXT NOT NULL,"
                "match_method TEXT NOT NULL,"
                "resolved_at TEXT NOT NULL)"
            )
            conn.execute(f"INSERT INTO {table}_v3 SELECT {columns} FROM {table}")
            conn.execute(f"DROP TABLE {table}")
            conn.execute(f"ALTER TABLE {table}_v3 RENAME TO {table}")

    def version(self) -> int:
        """R3.1 TRUTH: a valid initialized repository returns its
        numeric version; a missing/malformed version row is a schema
        contract violation (EnrichmentSchemaError); an operational
        SQLite failure is EnrichmentStorageError. NEVER a fake 0."""
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM enrichment_meta WHERE key = ?", (_VERSION_KEY,)
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"enrichment version read failed: {exc}"
            ) from exc
        if row is None:
            raise EnrichmentSchemaError("enrichment version row missing")
        raw = row[0]
        if not str(raw).isdigit() or int(raw) <= 0:
            raise EnrichmentSchemaError(f"invalid enrichment schema version: {raw!r}")
        version = int(raw)
        if version > CURRENT_ENRICHMENT_SCHEMA:
            # R3.2: a future version discovered after construction is
            # never returned as if valid.
            raise EnrichmentSchemaError(
                f"enrichment schema version {version} is newer "
                f"than supported {CURRENT_ENRICHMENT_SCHEMA}"
            )
        return version

    # -- identity authority (truthful writes) --------------------------------

    @staticmethod
    def _artist_identity_from_row(row) -> ArtistExternalIdentity:
        """R3.1: a malformed persistent identity row is CORRUPT USER
        AUTHORITY — it raises (never None, never silently skipped,
        never normalized into a valid mapping). None means absence."""
        key, external_id, status, method, resolved_at = row
        try:
            return ArtistExternalIdentity(
                local_artist_key=key,
                external_artist_id=external_id,
                status=IdentityStatus[status],
                match_method=MatchMethod[method],
                resolved_at=resolved_at,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EnrichmentStorageError(
                f"malformed artist identity row {key!r}: {exc}"
            ) from exc

    @staticmethod
    def _album_identity_from_row(row) -> AlbumExternalIdentity:
        """R3.1: malformed persistent album identity -> error (never
        None, never skipped)."""
        key, rg_id, release_id, status, method, resolved_at = row
        try:
            return AlbumExternalIdentity(
                local_album_key=key,
                release_group_id=rg_id,
                release_id=release_id,
                status=IdentityStatus[status],
                match_method=MatchMethod[method],
                resolved_at=resolved_at,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EnrichmentStorageError(
                f"malformed album identity row {key!r}: {exc}"
            ) from exc

    def save_artist_identity(self, identity: ArtistExternalIdentity) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO artist_identity(local_artist_key, "
                    "external_artist_id, status, match_method, resolved_at) "
                    "VALUES(?, ?, ?, ?, ?) "
                    "ON CONFLICT(local_artist_key) DO UPDATE SET "
                    "external_artist_id = excluded.external_artist_id, "
                    "status = excluded.status, "
                    "match_method = excluded.match_method, "
                    "resolved_at = excluded.resolved_at",
                    (
                        identity.local_artist_key,
                        identity.external_artist_id,
                        identity.status.name,
                        identity.match_method.name,
                        identity.resolved_at,
                    ),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"artist identity save failed: {exc}") from exc

    def save_album_identity(self, identity: AlbumExternalIdentity) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO album_identity(local_album_key, "
                    "release_group_id, release_id, status, match_method, "
                    "resolved_at) VALUES(?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(local_album_key) DO UPDATE SET "
                    "release_group_id = excluded.release_group_id, "
                    "release_id = excluded.release_id, "
                    "status = excluded.status, "
                    "match_method = excluded.match_method, "
                    "resolved_at = excluded.resolved_at",
                    (
                        identity.local_album_key,
                        identity.release_group_id,
                        identity.release_id,
                        identity.status.name,
                        identity.match_method.name,
                        identity.resolved_at,
                    ),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"album identity save failed: {exc}") from exc

    def delete_artist_identity(self, local_artist_key: str) -> None:
        self._delete_identity("artist_identity", "local_artist_key", local_artist_key)

    def delete_album_identity(self, local_album_key: str) -> None:
        self._delete_identity("album_identity", "local_album_key", local_album_key)

    def _delete_identity(self, table: str, column: str, key: str) -> None:
        """R2: identity DELETES are truthful — failures raise the
        normalized storage error instead of pretending success."""
        try:
            conn = self._connect()
            try:
                conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (key,))
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"{table} delete failed: {exc}") from exc

    def load_artist_identity(
        self, local_artist_key: str
    ) -> ArtistExternalIdentity | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT local_artist_key, external_artist_id, status, "
                    "match_method, resolved_at "
                    "FROM artist_identity WHERE local_artist_key = ?",
                    (local_artist_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"artist identity load failed: {exc}") from exc
        if row is None:
            return None
        identity = self._artist_identity_from_row(row)
        if identity.local_artist_key != local_artist_key:
            # R3.2: a key mismatch in IDENTITY AUTHORITY is corruption —
            # never converted to "no identity exists".
            raise EnrichmentStorageError(
                f"artist identity row key mismatch: "
                f"{identity.local_artist_key!r} != {local_artist_key!r}"
            )
        return identity

    def load_album_identity(self, local_album_key: str) -> AlbumExternalIdentity | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT local_album_key, release_group_id, release_id, "
                    "status, match_method, resolved_at "
                    "FROM album_identity WHERE local_album_key = ?",
                    (local_album_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"album identity load failed: {exc}") from exc
        if row is None:
            return None
        identity = self._album_identity_from_row(row)
        if identity.local_album_key != local_album_key:
            raise EnrichmentStorageError(
                f"album identity row key mismatch: "
                f"{identity.local_album_key!r} != {local_album_key!r}"
            )
        return identity

    def load_artist_identities(self) -> tuple[ArtistExternalIdentity, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_artist_key, external_artist_id, status, "
                    "match_method, resolved_at "
                    "FROM artist_identity ORDER BY local_artist_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"artist identity load all failed: {exc}"
            ) from exc
        # R3.1: identity authority corruption never yields a partial
        # result — any malformed row raises.
        return tuple(self._artist_identity_from_row(row) for row in rows)

    def load_album_identities(self) -> tuple[AlbumExternalIdentity, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_album_key, release_group_id, release_id, "
                    "status, match_method, resolved_at "
                    "FROM album_identity ORDER BY local_album_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"album identity load all failed: {exc}"
            ) from exc
        return tuple(self._album_identity_from_row(row) for row in rows)

    def clear_identities(self) -> None:
        """R3 TRANSACTIONAL: both identity tables are cleared atomically
        (BEGIN / COMMIT / ROLLBACK) — a failure can never leave a
        partially cleared identity authority. Truthful: raises
        EnrichmentStorageError on failure."""
        try:
            conn = self._connect()
            try:
                conn.execute("BEGIN")
                try:
                    conn.execute("DELETE FROM artist_identity")
                    conn.execute("DELETE FROM album_identity")
                    conn.execute("COMMIT")
                except Exception:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"identity clear failed: {exc}") from exc

    # -- knowledge (downloaded, best-effort cache) ---------------------------

    def save_artist_profile(self, profile: ArtistKnowledgeProfile) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO artist_knowledge(local_artist_key, profile) "
                    "VALUES(?, ?) "
                    "ON CONFLICT(local_artist_key) DO UPDATE SET "
                    "profile = excluded.profile",
                    (profile.local_artist_key, encode_artist_profile(profile)),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"artist knowledge save failed: {exc}"
            ) from exc

    def save_album_profile(self, profile: AlbumKnowledgeProfile) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO album_knowledge(local_album_key, profile) "
                    "VALUES(?, ?) "
                    "ON CONFLICT(local_album_key) DO UPDATE SET "
                    "profile = excluded.profile",
                    (profile.local_album_key, encode_album_profile(profile)),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"album knowledge save failed: {exc}") from exc

    def delete_artist_profile(self, local_artist_key: str) -> None:
        self._delete_knowledge("artist_knowledge", "local_artist_key", local_artist_key)

    def delete_album_profile(self, local_album_key: str) -> None:
        self._delete_knowledge("album_knowledge", "local_album_key", local_album_key)

    def _delete_knowledge(self, table: str, column: str, key: str) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (key,))
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"{table} delete failed: {exc}") from exc

    def load_artist_profile(
        self, local_artist_key: str
    ) -> ArtistKnowledgeProfile | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT profile FROM artist_knowledge WHERE local_artist_key = ?",
                    (local_artist_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"artist knowledge load failed: {exc}"
            ) from exc
        if row is None:
            return None
        profile = decode_artist_profile(row[0])
        if profile is None:
            logger.warning(
                "enrichment artist row %r malformed; skipping", local_artist_key
            )
            return None
        if profile.local_artist_key != local_artist_key:
            logger.warning(
                "enrichment artist row %r key mismatch; skipping", local_artist_key
            )
            return None
        return profile

    def load_album_profile(self, local_album_key: str) -> AlbumKnowledgeProfile | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT profile FROM album_knowledge WHERE local_album_key = ?",
                    (local_album_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"album knowledge load failed: {exc}") from exc
        if row is None:
            return None
        profile = decode_album_profile(row[0])
        if profile is None:
            logger.warning(
                "enrichment album row %r malformed; skipping", local_album_key
            )
            return None
        if profile.local_album_key != local_album_key:
            logger.warning(
                "enrichment album row %r key mismatch; skipping", local_album_key
            )
            return None
        return profile

    def load_artist_profiles(self) -> tuple[ArtistKnowledgeProfile, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_artist_key, profile FROM artist_knowledge "
                    "ORDER BY local_artist_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"artist knowledge load all failed: {exc}"
            ) from exc
        profiles = []
        for key, raw in rows:
            profile = decode_artist_profile(raw)
            if profile is None:
                logger.warning("enrichment artist row %r malformed; skipping", key)
                continue
            if profile.local_artist_key != key:
                logger.warning("enrichment artist row %r key mismatch; skipping", key)
                continue
            profiles.append(profile)
        return tuple(profiles)

    def load_album_profiles(self) -> tuple[AlbumKnowledgeProfile, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_album_key, profile FROM album_knowledge "
                    "ORDER BY local_album_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(
                f"album knowledge load all failed: {exc}"
            ) from exc
        profiles = []
        for key, raw in rows:
            profile = decode_album_profile(raw)
            if profile is None:
                logger.warning("enrichment album row %r malformed; skipping", key)
                continue
            if profile.local_album_key != key:
                logger.warning("enrichment album row %r key mismatch; skipping", key)
                continue
            profiles.append(profile)
        return tuple(profiles)

    def clear_knowledge(self) -> None:
        """Clear DOWNLOADED KNOWLEDGE only — the identity authority rows
        (including manual mappings) are preserved (R1/R2).

        R3 TRANSACTIONAL: both knowledge tables are cleared atomically;
        failures raise EnrichmentStorageError (never a fake success)."""
        try:
            conn = self._connect()
            try:
                conn.execute("BEGIN")
                try:
                    conn.execute("DELETE FROM artist_knowledge")
                    conn.execute("DELETE FROM album_knowledge")
                    conn.execute("COMMIT")
                except Exception:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise EnrichmentStorageError(f"knowledge clear failed: {exc}") from exc


# Backward-compatible alias: M6.9A named this class SqliteKnowledgeRepository.
SqliteKnowledgeRepository = SqliteEnrichmentRepository
