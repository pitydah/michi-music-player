"""SQLite enrichment repository (M6.9A-R1) — enrichment.db EXCLUSIVELY.

M6.9A LIBRARY INDEX FIREWALL: enrichment owns its own database file and
its own tables. The canonical ``library_index`` / ``library_meta`` tables
are NEVER touched — no shared schema, no shared version key, no
cross-writes. External knowledge can never enter the library index.

R1: ONE schema owner (this class implements BOTH ``KnowledgeRepositoryPort``
and ``IdentityRepositoryPort`` — identity authority and downloaded
knowledge are different TABLES, same database). Schema 2 adds
``artist_identity`` / ``album_identity``; migration 1 -> 2 is
transactional and preserves existing knowledge profiles.
"""

import contextlib
import logging
import sqlite3
from pathlib import Path

from michi.application.enrichment_ports import (
    IdentityRepositoryPort,
    KnowledgeRepositoryPort,
)
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumKnowledgeProfile,
    ArtistExternalIdentity,
    ArtistKnowledgeProfile,
    IdentityStatus,
    MatchMethod,
    decode_album_profile,
    decode_artist_profile,
    encode_album_profile,
    encode_artist_profile,
)

logger = logging.getLogger(__name__)

CURRENT_ENRICHMENT_SCHEMA = 2
_VERSION_KEY = "enrichment_schema_version"


class EnrichmentSchemaError(RuntimeError):
    """The enrichment database schema is newer than this build supports."""


class SqliteEnrichmentRepository(KnowledgeRepositoryPort, IdentityRepositoryPort):
    """Single schema authority for enrichment.db (best effort: sqlite
    errors are logged, never raised — enrichment failure must never hurt
    the canonical library)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(str(self._db_path), isolation_level=None)

    # -- schema (single owner) ----------------------------------------------

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
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
            conn.execute(
                "CREATE TABLE IF NOT EXISTS enrichment_meta ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = conn.execute(
                "SELECT value FROM enrichment_meta WHERE key = ?", (_VERSION_KEY,)
            ).fetchone()
            raw = row[0] if row is not None else None
            if raw is None:
                self._create_identity_tables(conn)
                conn.execute(
                    "INSERT INTO enrichment_meta(key, value) VALUES(?, ?)",
                    (_VERSION_KEY, str(CURRENT_ENRICHMENT_SCHEMA)),
                )
                return
            version = int(raw) if str(raw).isdigit() else 0
            if version > CURRENT_ENRICHMENT_SCHEMA:
                raise EnrichmentSchemaError(
                    f"enrichment schema version {version} is newer "
                    f"than supported {CURRENT_ENRICHMENT_SCHEMA}"
                )
            if version == 1:
                # MIGRATION 1 -> 2 (R1): add identity tables; knowledge
                # profiles survive. Transactional — a failure never
                # leaves the schema half-migrated.
                conn.execute("BEGIN")
                try:
                    self._create_identity_tables(conn)
                    conn.execute(
                        "UPDATE enrichment_meta SET value = ? WHERE key = ?",
                        (str(CURRENT_ENRICHMENT_SCHEMA), _VERSION_KEY),
                    )
                    conn.execute("COMMIT")
                except Exception:
                    with contextlib.suppress(sqlite3.Error):
                        conn.execute("ROLLBACK")
                    raise
                return
            # version 0 or 2: idempotent — ensure identity tables exist.
            self._create_identity_tables(conn)
            if version == 0:
                conn.execute(
                    "UPDATE enrichment_meta SET value = ? WHERE key = ?",
                    (str(CURRENT_ENRICHMENT_SCHEMA), _VERSION_KEY),
                )
        finally:
            conn.close()

    @staticmethod
    def _create_identity_tables(conn) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS artist_identity ("
            "local_artist_key TEXT PRIMARY KEY,"
            "external_artist_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "manually_confirmed INTEGER NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS album_identity ("
            "local_album_key TEXT PRIMARY KEY,"
            "release_group_id TEXT NOT NULL,"
            "release_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "match_method TEXT NOT NULL,"
            "manually_confirmed INTEGER NOT NULL,"
            "resolved_at TEXT NOT NULL)"
        )

    def version(self) -> int:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT value FROM enrichment_meta WHERE key = ?", (_VERSION_KEY,)
                ).fetchone()
            finally:
                conn.close()
            if row is None:
                return 0
            return int(row[0]) if str(row[0]).isdigit() else 0
        except sqlite3.Error as exc:
            logger.warning("enrichment version read failed: %s", exc)
            return 0

    # -- identity authority ------------------------------------------------

    @staticmethod
    def _artist_identity_from_row(row) -> ArtistExternalIdentity | None:
        key, external_id, status, method, confirmed, resolved_at = row
        try:
            return ArtistExternalIdentity(
                local_artist_key=key,
                external_artist_id=external_id,
                status=IdentityStatus[status],
                match_method=MatchMethod[method],
                manually_confirmed=bool(confirmed),
                resolved_at=resolved_at,
            )
        except (KeyError, ValueError):
            logger.warning("enrichment artist identity row %r malformed; skipping", key)
            return None

    @staticmethod
    def _album_identity_from_row(row) -> AlbumExternalIdentity | None:
        key, rg_id, release_id, status, method, confirmed, resolved_at = row
        try:
            return AlbumExternalIdentity(
                local_album_key=key,
                release_group_id=rg_id,
                release_id=release_id,
                status=IdentityStatus[status],
                match_method=MatchMethod[method],
                manually_confirmed=bool(confirmed),
                resolved_at=resolved_at,
            )
        except (KeyError, ValueError):
            logger.warning("enrichment album identity row %r malformed; skipping", key)
            return None

    def save_artist_identity(self, identity: ArtistExternalIdentity) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO artist_identity(local_artist_key, "
                    "external_artist_id, status, match_method, "
                    "manually_confirmed, resolved_at) VALUES(?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(local_artist_key) DO UPDATE SET "
                    "external_artist_id = excluded.external_artist_id, "
                    "status = excluded.status, "
                    "match_method = excluded.match_method, "
                    "manually_confirmed = excluded.manually_confirmed, "
                    "resolved_at = excluded.resolved_at",
                    (
                        identity.local_artist_key,
                        identity.external_artist_id,
                        identity.status.name,
                        identity.match_method.name,
                        int(identity.manually_confirmed),
                        identity.resolved_at,
                    ),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment artist identity save failed: %s", exc)

    def save_album_identity(self, identity: AlbumExternalIdentity) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO album_identity(local_album_key, "
                    "release_group_id, release_id, status, match_method, "
                    "manually_confirmed, resolved_at) VALUES(?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(local_album_key) DO UPDATE SET "
                    "release_group_id = excluded.release_group_id, "
                    "release_id = excluded.release_id, "
                    "status = excluded.status, "
                    "match_method = excluded.match_method, "
                    "manually_confirmed = excluded.manually_confirmed, "
                    "resolved_at = excluded.resolved_at",
                    (
                        identity.local_album_key,
                        identity.release_group_id,
                        identity.release_id,
                        identity.status.name,
                        identity.match_method.name,
                        int(identity.manually_confirmed),
                        identity.resolved_at,
                    ),
                )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment album identity save failed: %s", exc)

    def delete_artist_identity(self, local_artist_key: str) -> None:
        self._delete("artist_identity", "local_artist_key", local_artist_key)

    def delete_album_identity(self, local_album_key: str) -> None:
        self._delete("album_identity", "local_album_key", local_album_key)

    def _delete(self, table: str, column: str, key: str) -> None:
        try:
            conn = self._connect()
            try:
                conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (key,))
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment identity delete failed: %s", exc)

    def load_artist_identity(
        self, local_artist_key: str
    ) -> ArtistExternalIdentity | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT local_artist_key, external_artist_id, status, "
                    "match_method, manually_confirmed, resolved_at "
                    "FROM artist_identity WHERE local_artist_key = ?",
                    (local_artist_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment artist identity load failed: %s", exc)
            return None
        if row is None:
            return None
        identity = self._artist_identity_from_row(row)
        if identity is not None and identity.local_artist_key != local_artist_key:
            logger.warning("enrichment artist identity row key mismatch; skipping")
            return None
        return identity

    def load_album_identity(self, local_album_key: str) -> AlbumExternalIdentity | None:
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT local_album_key, release_group_id, release_id, "
                    "status, match_method, manually_confirmed, resolved_at "
                    "FROM album_identity WHERE local_album_key = ?",
                    (local_album_key,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment album identity load failed: %s", exc)
            return None
        if row is None:
            return None
        identity = self._album_identity_from_row(row)
        if identity is not None and identity.local_album_key != local_album_key:
            logger.warning("enrichment album identity row key mismatch; skipping")
            return None
        return identity

    def load_artist_identities(self) -> tuple[ArtistExternalIdentity, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_artist_key, external_artist_id, status, "
                    "match_method, manually_confirmed, resolved_at "
                    "FROM artist_identity ORDER BY local_artist_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment artist identity load all failed: %s", exc)
            return ()
        identities = []
        for row in rows:
            identity = self._artist_identity_from_row(row)
            if identity is not None:
                identities.append(identity)
        return tuple(identities)

    def load_album_identities(self) -> tuple[AlbumExternalIdentity, ...]:
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT local_album_key, release_group_id, release_id, "
                    "status, match_method, manually_confirmed, resolved_at "
                    "FROM album_identity ORDER BY local_album_key"
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment album identity load all failed: %s", exc)
            return ()
        identities = []
        for row in rows:
            identity = self._album_identity_from_row(row)
            if identity is not None:
                identities.append(identity)
        return tuple(identities)

    def clear_identities(self) -> None:
        """Remove ALL identity authority rows (explicit, never accidental:
        the generic clear() of M6.9A no longer exists)."""
        try:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM artist_identity")
                conn.execute("DELETE FROM album_identity")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment identity clear failed: %s", exc)

    # -- knowledge (downloaded) ---------------------------------------------

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
            logger.warning("enrichment artist save failed: %s", exc)

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
            logger.warning("enrichment album save failed: %s", exc)

    def delete_artist_profile(self, local_artist_key: str) -> None:
        self._delete("artist_knowledge", "local_artist_key", local_artist_key)

    def delete_album_profile(self, local_album_key: str) -> None:
        self._delete("album_knowledge", "local_album_key", local_album_key)

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
            logger.warning("enrichment artist load failed: %s", exc)
            return None
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
            logger.warning("enrichment album load failed: %s", exc)
            return None
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
            logger.warning("enrichment artist load all failed: %s", exc)
            return ()
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
            logger.warning("enrichment album load all failed: %s", exc)
            return ()
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
        (including manual mappings) are preserved (R1)."""
        try:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM artist_knowledge")
                conn.execute("DELETE FROM album_knowledge")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment knowledge clear failed: %s", exc)


# Backward-compatible alias: M6.9A named this class SqliteKnowledgeRepository.
SqliteKnowledgeRepository = SqliteEnrichmentRepository
