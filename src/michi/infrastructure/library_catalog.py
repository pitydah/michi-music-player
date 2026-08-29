"""Authoritative library catalog persistence (M6-EXT-R4).

The catalog (LibrarySource / MediaFileRecord / TrackRecord / stable
identities) is USER AUTHORITY — deliberately separate from the rebuildable
library index cache. Contracts:

- FAIL CLOSED schema: brand-new database → transactional initialize;
  current version → validate required shape; future version → error;
  malformed version → error; missing authoritative table → error. Missing
  authoritative tables are NEVER recreated empty.
- TRUTHFUL writes: an authoritative operation succeeds only when its write
  committed; storage failures raise ``LibraryCatalogStorageError``.
- FOREIGN KEYS ON per connection (connection-local in Python sqlite3);
  ON DELETE RESTRICT — user-facing identity is never cascade-deleted.
"""

import sqlite3

from michi.application.library_port import (
    LibraryCatalogPort,
    LibraryCatalogSchemaError,
    LibraryCatalogStorageError,
)
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceLifecycle,
    TrackRecord,
)

CATALOG_SCHEMA_VERSION = 1

# Shared DDL (also consumed by the R4-D transactional migration so the
# schema shape lives in exactly one place).
CATALOG_SCHEMA_DDL = (
    """
    CREATE TABLE library_catalog_meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE library_sources (
        library_source_id TEXT PRIMARY KEY,
        display_name      TEXT NOT NULL,
        root_path         TEXT NOT NULL,
        enabled           INTEGER NOT NULL CHECK (enabled IN (0, 1)),
        lifecycle         TEXT NOT NULL,
        created_at_ms     INTEGER NOT NULL,
        updated_at_ms     INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE library_media_files (
        media_file_id      TEXT PRIMARY KEY,
        library_source_id  TEXT NULL,
        relative_path      TEXT NULL,
        last_known_path    TEXT NOT NULL,
        availability       TEXT NOT NULL,
        created_at_ms      INTEGER NOT NULL,
        updated_at_ms      INTEGER NOT NULL,
        FOREIGN KEY(library_source_id)
            REFERENCES library_sources(library_source_id)
            ON DELETE RESTRICT,
        UNIQUE(library_source_id, relative_path)
    )
    """,
    """
    CREATE TABLE library_tracks (
        track_id      TEXT PRIMARY KEY,
        media_file_id TEXT NOT NULL,
        created_at_ms INTEGER NOT NULL,
        FOREIGN KEY(media_file_id)
            REFERENCES library_media_files(media_file_id)
            ON DELETE RESTRICT
    )
    """,
)

_VERSION_KEY = "schema_version"
_CATALOG_TABLES = (
    "library_catalog_meta",
    "library_sources",
    "library_media_files",
    "library_tracks",
)


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


class SqliteLibraryCatalogRepository(LibraryCatalogPort):
    """Authoritative catalog repository in the MAIN Michi database.

    ``isolation_level=None`` (autocommit) + explicit transactions keeps every
    authoritative mutation atomic; foreign keys are enabled per connection.
    """

    def __init__(self, db_path) -> None:
        self._db_path = db_path

    # ------------------------------------------------------------------ schema

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        self._validate_or_initialize(conn)
        return conn

    def _validate_or_initialize(self, conn: sqlite3.Connection) -> None:
        existing = self._table_names(conn)
        meta_present = "library_catalog_meta" in existing

        if not meta_present:
            if existing & set(_CATALOG_TABLES):
                # Some catalog tables exist but the version metadata is
                # missing: malformed authoritative state — fail closed.
                raise LibraryCatalogSchemaError(
                    "catalog tables exist without library_catalog_meta; "
                    "refusing to guess the schema version"
                )
            # Brand-new empty catalog: transactionally initialize.
            self._initialize(conn)
            return

        version = self._read_version(conn)
        if version != CATALOG_SCHEMA_VERSION:
            raise LibraryCatalogSchemaError(
                f"unsupported catalog schema version {version!r} "
                f"(supported: {CATALOG_SCHEMA_VERSION})"
            )
        missing = set(_CATALOG_TABLES) - existing
        if missing:
            raise LibraryCatalogSchemaError(
                "catalog schema is versioned current but missing "
                f"authoritative tables: {sorted(missing)}"
            )

    @staticmethod
    def _table_names(conn: sqlite3.Connection) -> set[str]:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row[0] for row in rows}

    def _read_version(self, conn: sqlite3.Connection) -> int | None:
        row = conn.execute(
            "SELECT value FROM library_catalog_meta WHERE key = ?",
            (_VERSION_KEY,),
        ).fetchone()
        if row is None:
            return None
        raw = row[0]
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise LibraryCatalogSchemaError(
                f"malformed catalog schema version {raw!r}"
            ) from exc

    def _initialize(self, conn: sqlite3.Connection) -> None:
        try:
            conn.execute("BEGIN IMMEDIATE")
            for statement in CATALOG_SCHEMA_DDL:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO library_catalog_meta(key, value) VALUES(?, ?)",
                (_VERSION_KEY, str(CATALOG_SCHEMA_VERSION)),
            )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog initialization failed: {exc}"
            ) from exc

    # ------------------------------------------------------------- read paths

    def schema_version(self) -> int:
        conn = self._connect()
        try:
            version = self._read_version(conn)
        finally:
            conn.close()
        if version != CATALOG_SCHEMA_VERSION:
            raise LibraryCatalogSchemaError(
                f"unsupported catalog schema version {version!r}"
            )
        return version

    def load_sources(self) -> tuple[LibrarySource, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT library_source_id, display_name, root_path, enabled, "
                "lifecycle FROM library_sources ORDER BY display_name"
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"catalog sources load failed: {exc}"
            ) from exc
        finally:
            conn.close()
        return tuple(
            LibrarySource(
                library_source_id=row[0],
                display_name=row[1],
                root_path=row[2],
                enabled=bool(row[3]),
                lifecycle=SourceLifecycle(row[4]),
            )
            for row in rows
        )

    def load_media(self) -> tuple[MediaFileRecord, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT media_file_id, library_source_id, relative_path, "
                "last_known_path, availability FROM library_media_files "
                "ORDER BY media_file_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"catalog media load failed: {exc}"
            ) from exc
        finally:
            conn.close()
        return tuple(self._media_from_row(row) for row in rows)

    def load_tracks(self) -> tuple[TrackRecord, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT track_id, media_file_id, created_at_ms "
                "FROM library_tracks ORDER BY track_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"catalog tracks load failed: {exc}"
            ) from exc
        finally:
            conn.close()
        return tuple(
            TrackRecord(track_id=row[0], media_file_id=row[1], created_at_ms=row[2])
            for row in rows
        )

    def media_for_source(self, source_id: str) -> tuple[MediaFileRecord, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT media_file_id, library_source_id, relative_path, "
                "last_known_path, availability FROM library_media_files "
                "WHERE library_source_id = ? ORDER BY relative_path",
                (source_id,),
            ).fetchall()
        except sqlite3.Error as exc:
            raise LibraryCatalogStorageError(
                f"catalog media-for-source load failed: {exc}"
            ) from exc
        finally:
            conn.close()
        return tuple(self._media_from_row(row) for row in rows)

    @staticmethod
    def _media_from_row(row) -> MediaFileRecord:
        return MediaFileRecord(
            media_file_id=row[0],
            library_source_id=row[1],
            relative_path=row[2],
            last_known_path=row[3],
            availability=MediaAvailability(row[4]),
        )

    # ------------------------------------------------------------ write paths

    def upsert_source(self, source: LibrarySource) -> None:
        now = _now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO library_sources(library_source_id, display_name, "
                "root_path, enabled, lifecycle, created_at_ms, updated_at_ms) "
                "VALUES(?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(library_source_id) DO UPDATE SET "
                "display_name = excluded.display_name, "
                "root_path = excluded.root_path, "
                "enabled = excluded.enabled, "
                "lifecycle = excluded.lifecycle, "
                "updated_at_ms = excluded.updated_at_ms",
                (
                    source.library_source_id,
                    source.display_name,
                    source.root_path,
                    int(source.enabled),
                    source.lifecycle.value,
                    now,
                    now,
                ),
            )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog source write failed: {exc}"
            ) from exc
        finally:
            conn.close()

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        self._update_source_fields(
            source_id, {"enabled": int(enabled)}
        )

    def retire_source(self, source_id: str) -> None:
        self._update_source_fields(
            source_id, {"lifecycle": SourceLifecycle.RETIRED.value}
        )

    def _update_source_fields(self, source_id: str, fields: dict) -> None:
        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values())
        now = _now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                f"UPDATE library_sources SET {assignments}, updated_at_ms = ? "
                "WHERE library_source_id = ?",
                (*values, now, source_id),
            )
            if cursor.rowcount == 0:
                raise LibraryCatalogStorageError(
                    f"catalog source not found: {source_id}"
                )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog source update failed: {exc}"
            ) from exc
        finally:
            conn.close()

    def upsert_media(self, records: tuple[MediaFileRecord, ...]) -> None:
        if not records:
            return
        now = _now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for record in records:
                conn.execute(
                    "INSERT INTO library_media_files(media_file_id, "
                    "library_source_id, relative_path, last_known_path, "
                    "availability, created_at_ms, updated_at_ms) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(media_file_id) DO UPDATE SET "
                    "library_source_id = excluded.library_source_id, "
                    "relative_path = excluded.relative_path, "
                    "last_known_path = excluded.last_known_path, "
                    "availability = excluded.availability, "
                    "updated_at_ms = excluded.updated_at_ms",
                    (
                        record.media_file_id,
                        record.library_source_id,
                        record.relative_path,
                        record.last_known_path,
                        record.availability.value,
                        now,
                        now,
                    ),
                )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog media write failed: {exc}"
            ) from exc
        finally:
            conn.close()

    def mark_media_availability(
        self, media_id: str, availability: MediaAvailability
    ) -> None:
        now = _now_ms()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "UPDATE library_media_files SET availability = ?, "
                "updated_at_ms = ? WHERE media_file_id = ?",
                (availability.value, now, media_id),
            )
            if cursor.rowcount == 0:
                raise LibraryCatalogStorageError(
                    f"catalog media not found: {media_id}"
                )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog media availability write failed: {exc}"
            ) from exc
        finally:
            conn.close()

    def upsert_tracks(self, tracks: tuple[TrackRecord, ...]) -> None:
        if not tracks:
            return
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for track in tracks:
                conn.execute(
                    "INSERT INTO library_tracks(track_id, media_file_id, "
                    "created_at_ms) VALUES(?, ?, ?) "
                    "ON CONFLICT(track_id) DO UPDATE SET "
                    "media_file_id = excluded.media_file_id, "
                    "created_at_ms = excluded.created_at_ms",
                    (track.track_id, track.media_file_id, track.created_at_ms),
                )
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise LibraryCatalogStorageError(
                f"catalog tracks write failed: {exc}"
            ) from exc
        finally:
            conn.close()
