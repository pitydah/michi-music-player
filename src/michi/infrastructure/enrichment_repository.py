"""SQLite knowledge repository (M6.9A) — enrichment.db EXCLUSIVELY.

M6.9A LIBRARY INDEX FIREWALL: enrichment owns its own database file and
its own tables (``artist_knowledge``, ``album_knowledge``,
``enrichment_meta``). The canonical ``library_index`` / ``library_meta``
tables are NEVER touched — no shared schema, no shared version key, no
cross-writes. External knowledge can never enter the library index.
"""

import logging
import sqlite3
from pathlib import Path

from michi.application.enrichment_ports import KnowledgeRepositoryPort
from michi.domain.enrichment import (
    AlbumKnowledgeProfile,
    ArtistKnowledgeProfile,
    decode_album_profile,
    decode_artist_profile,
    encode_album_profile,
    encode_artist_profile,
)

logger = logging.getLogger(__name__)

CURRENT_ENRICHMENT_SCHEMA = 1
_VERSION_KEY = "enrichment_schema_version"


class EnrichmentSchemaError(RuntimeError):
    """The enrichment database schema is newer than this build supports."""


class SqliteKnowledgeRepository(KnowledgeRepositoryPort):
    """Best-effort persistence for knowledge profiles (never raises on
    sqlite errors — enrichment failure must never hurt the canonical
    library)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(str(self._db_path), isolation_level=None)

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
                conn.execute(
                    "INSERT INTO enrichment_meta(key, value) VALUES(?, ?)",
                    (_VERSION_KEY, str(CURRENT_ENRICHMENT_SCHEMA)),
                )
            else:
                version = int(raw) if str(raw).isdigit() else 0
                if version > CURRENT_ENRICHMENT_SCHEMA:
                    raise EnrichmentSchemaError(
                        f"enrichment schema version {version} is newer "
                        f"than supported {CURRENT_ENRICHMENT_SCHEMA}"
                    )
                if version == 0:
                    conn.execute(
                        "UPDATE enrichment_meta SET value = ? WHERE key = ?",
                        (str(CURRENT_ENRICHMENT_SCHEMA), _VERSION_KEY),
                    )
        finally:
            conn.close()

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

    # -- artist profiles ---------------------------------------------------

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
            profiles.append(profile)
        return tuple(profiles)

    # -- album profiles ----------------------------------------------------

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
        return profile

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
            profiles.append(profile)
        return tuple(profiles)

    def clear(self) -> None:
        """Clear enrichment knowledge ONLY — the canonical library tables
        are owned elsewhere and never even named here."""
        try:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM artist_knowledge")
                conn.execute("DELETE FROM album_knowledge")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("enrichment clear failed: %s", exc)
