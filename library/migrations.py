"""Versioned SQLite migrations for the Michi catalogue.

Migrations are deliberately idempotent. Michi has databases created by several
historical schema paths, so an ``ALTER TABLE ... ADD COLUMN`` is skipped when the
column already exists instead of aborting startup. Every migration still runs
inside a transaction and is recorded with a checksum.
"""
from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from collections.abc import Iterable

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "_migrations"

# Each migration: (version, description, sql_up, sql_down)
MIGRATIONS = [
    (1, "Initial schema", """
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            directory TEXT NOT NULL,
            ext TEXT NOT NULL,
            kind TEXT NOT NULL,
            size INTEGER,
            mtime REAL,
            duration REAL,
            channels INTEGER,
            sample_rate INTEGER,
            bitrate INTEGER,
            title TEXT,
            artist TEXT,
            album TEXT,
            year INTEGER,
            genre TEXT,
            track_number INTEGER,
            composer TEXT,
            date_added REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cover_path TEXT DEFAULT '',
            cover_type TEXT DEFAULT 'mosaic',
            description TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath TEXT NOT NULL,
            track_id INTEGER REFERENCES media_items(id),
            position INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY,
            filepath TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT NOT NULL,
            device TEXT DEFAULT 'desktop',
            played_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE,
            device TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS album_art_cache (
            album_hash TEXT PRIMARY KEY,
            mime TEXT,
            data BLOB
        );
        CREATE TABLE IF NOT EXISTS detected_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT,
            year INTEGER,
            genre TEXT,
            duration REAL,
            source TEXT DEFAULT '',
            provider TEXT DEFAULT '',
            confidence REAL,
            isrc TEXT,
            artwork_url TEXT,
            external_url TEXT,
            filepath TEXT,
            matched_library_id INTEGER,
            raw_json TEXT,
            detected_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scan_roots (
            path TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            last_scan_started REAL,
            last_scan_finished REAL,
            file_count INTEGER DEFAULT 0,
            added_count INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            missing_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS index_errors (
            filepath TEXT,
            error TEXT,
            stage TEXT,
            updated_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS library_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 1,
            last_scan REAL,
            file_count INTEGER DEFAULT 0,
            added_count INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            missing_count INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS track_genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
            genre TEXT NOT NULL,
            canonical_genre TEXT NOT NULL DEFAULT '',
            original_value TEXT NOT NULL DEFAULT '',
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'tag',
            is_manual INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL,
            UNIQUE(track_id, genre)
        );
        CREATE TABLE IF NOT EXISTS genre_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL UNIQUE,
            canonical_genre TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'builtin',
            is_builtin INTEGER DEFAULT 0,
            is_user_defined INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL
        );
    """, """
        DROP TABLE IF EXISTS genre_aliases;
        DROP TABLE IF EXISTS track_genres;
        DROP TABLE IF EXISTS library_roots;
        DROP TABLE IF EXISTS index_errors;
        DROP TABLE IF EXISTS scan_roots;
        DROP TABLE IF EXISTS detected_tracks;
        DROP TABLE IF EXISTS album_art_cache;
        DROP TABLE IF EXISTS favorites;
        DROP TABLE IF EXISTS play_history;
        DROP TABLE IF EXISTS queue_state;
        DROP TABLE IF EXISTS playlist_items;
        DROP TABLE IF EXISTS playlists;
        DROP TABLE IF EXISTS media_items;
    """),
    (2, "Add stable identity columns", """
        ALTER TABLE media_items ADD COLUMN track_uid TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN content_hash TEXT DEFAULT '';
    """, """
        ALTER TABLE media_items DROP COLUMN track_uid;
        ALTER TABLE media_items DROP COLUMN content_hash;
    """),
    (3, "Add processed signature and format columns", """
        ALTER TABLE media_items ADD COLUMN mtime_processed REAL DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN file_size INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN format TEXT DEFAULT '';
    """, """
        ALTER TABLE media_items DROP COLUMN mtime_processed;
        ALTER TABLE media_items DROP COLUMN file_size;
        ALTER TABLE media_items DROP COLUMN format;
    """),
    (4, "Add album artist and disc number", """
        ALTER TABLE media_items ADD COLUMN albumartist TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN disc_number INTEGER DEFAULT 0;
    """, """
        DROP INDEX IF EXISTS idx_media_albumartist;
        ALTER TABLE media_items DROP COLUMN albumartist;
        ALTER TABLE media_items DROP COLUMN disc_number;
    """),
    (5, "Add canonical playback fields", """
        ALTER TABLE media_items ADD COLUMN rating INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN play_count INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN last_played REAL;
    """, """
        ALTER TABLE media_items DROP COLUMN last_played;
        ALTER TABLE media_items DROP COLUMN play_count;
        ALTER TABLE media_items DROP COLUMN rating;
    """),
    (6, "Normalized metadata keys and optimized library indexes", """
        ALTER TABLE media_items ADD COLUMN track_total INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN disc_total INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN album_key TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN deleted_at REAL;
        ALTER TABLE media_items ADD COLUMN scan_status TEXT DEFAULT 'ok';
        ALTER TABLE media_items ADD COLUMN normalized_title TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN normalized_artist TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN normalized_album TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN normalized_albumartist TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN metadata_source TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN metadata_confidence REAL DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN metadata_completeness INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN metadata_issues TEXT DEFAULT '[]';
        ALTER TABLE media_items ADD COLUMN metadata_hash TEXT DEFAULT '';

        CREATE INDEX IF NOT EXISTS idx_media_active_norm_title
            ON media_items(normalized_title, id) WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_norm_artist_album
            ON media_items(normalized_albumartist, normalized_album, id)
            WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_album_tracks
            ON media_items(album_key, disc_number, track_number, id)
            WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_year_album
            ON media_items(year DESC, normalized_album, id)
            WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_directory
            ON media_items(directory, id) WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_format
            ON media_items(ext, id) WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_active_last_played
            ON media_items(last_played DESC, id) WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_media_metadata_health
            ON media_items(metadata_completeness, id) WHERE deleted_at IS NULL;
        CREATE INDEX IF NOT EXISTS idx_play_history_track_time
            ON play_history(track_id, played_at DESC);
    """, """
        DROP INDEX IF EXISTS idx_play_history_track_time;
        DROP INDEX IF EXISTS idx_media_metadata_health;
        DROP INDEX IF EXISTS idx_media_active_last_played;
        DROP INDEX IF EXISTS idx_media_active_format;
        DROP INDEX IF EXISTS idx_media_active_directory;
        DROP INDEX IF EXISTS idx_media_active_year_album;
        DROP INDEX IF EXISTS idx_media_active_album_tracks;
        DROP INDEX IF EXISTS idx_media_active_norm_artist_album;
        DROP INDEX IF EXISTS idx_media_active_norm_title;
    """),
]

_ADD_COLUMN = re.compile(
    r"^ALTER\s+TABLE\s+([\w]+)\s+ADD\s+COLUMN\s+([\w]+)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.DatabaseError:
        return set()


def _statements(sql: str) -> Iterable[str]:
    """Yield complete statements from migration SQL."""
    buffer = ""
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer += (" " if buffer else "") + stripped
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip().rstrip(";").strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        yield buffer.strip().rstrip(";")


def _execute_statement(conn: sqlite3.Connection, statement: str) -> None:
    match = _ADD_COLUMN.match(statement)
    if match:
        table, column, definition = match.groups()
        if column in _table_columns(conn, table):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return
    conn.execute(statement)


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")


def get_current_version(conn: sqlite3.Connection) -> int:
    ensure_migrations_table(conn)
    row = conn.execute(f"SELECT MAX(version) FROM {MIGRATIONS_TABLE}").fetchone()
    return int(row[0]) if row and row[0] else 0


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT DEFAULT (datetime('now')),
            checksum TEXT DEFAULT ''
        )
    """)


def _migrate_legacy_playcount(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "media_items")
    if "playcount" in columns and "play_count" in columns:
        conn.execute(
            "UPDATE media_items SET play_count=playcount "
            "WHERE COALESCE(play_count, 0)=0 AND COALESCE(playcount, 0)>0"
        )


def _select_expression(columns: set[str], name: str, default_sql: str) -> str:
    if name in columns:
        return name
    return f"{default_sql} AS {name}"


def _backfill_metadata_keys(conn: sqlite3.Connection, batch_size: int = 500) -> None:
    """Backfill normalized metadata even on incomplete historical schemas."""
    columns = _table_columns(conn, "media_items")
    target_columns = {
        "normalized_title", "normalized_artist", "normalized_album",
        "normalized_albumartist", "metadata_source", "metadata_confidence",
        "metadata_completeness", "metadata_issues", "metadata_hash",
    }
    if not target_columns.issubset(columns):
        return

    from library.metadata_normalizer import enrich_index_record

    source_defaults = {
        "filepath": "''",
        "filename": "''",
        "title": "''",
        "artist": "''",
        "album": "''",
        "albumartist": "''",
        "year": "0",
        "genre": "''",
        "track_number": "0",
        "track_total": "0",
        "disc_number": "0",
        "disc_total": "0",
        "composer": "''",
        "isrc": "''",
        "mb_track_id": "''",
        "mb_album_id": "''",
        "duration": "0",
        "sample_rate": "0",
        "channels": "0",
    }
    source_names = list(source_defaults)
    select_list = ", ".join(
        _select_expression(columns, name, source_defaults[name])
        for name in source_names
    )
    cursor = conn.execute(
        f"SELECT id, {select_list} FROM media_items "
        "WHERE COALESCE(normalized_title, '')='' "
        "OR COALESCE(metadata_hash, '')=''"
    )

    total = 0
    while True:
        rows = cursor.fetchmany(max(1, int(batch_size)))
        if not rows:
            break
        updates = []
        for row in rows:
            record = {
                name: row[index + 1]
                for index, name in enumerate(source_names)
            }
            enriched = enrich_index_record(record)
            updates.append((
                enriched["normalized_title"],
                enriched["normalized_artist"],
                enriched["normalized_album"],
                enriched["normalized_albumartist"],
                enriched["metadata_source"],
                enriched["metadata_confidence"],
                enriched["metadata_completeness"],
                enriched["metadata_issues"],
                enriched["metadata_hash"],
                row[0],
            ))
        conn.executemany(
            "UPDATE media_items SET normalized_title=?, normalized_artist=?, "
            "normalized_album=?, normalized_albumartist=?, metadata_source=?, "
            "metadata_confidence=?, metadata_completeness=?, metadata_issues=?, "
            "metadata_hash=? WHERE id=?",
            updates,
        )
        total += len(updates)
    if total:
        logger.info("Backfilled normalized metadata for %d catalogue rows", total)


def migrate(conn: sqlite3.Connection, target_version: int | None = None,
            backup_path: str | None = None) -> None:
    _configure_connection(conn)
    ensure_migrations_table(conn)
    current = get_current_version(conn)
    if backup_path:
        escaped = str(backup_path).replace("'", "''")
        conn.execute(f"VACUUM INTO '{escaped}'")

    target = target_version or max(migration[0] for migration in MIGRATIONS)
    for version, description, sql_up, _sql_down in MIGRATIONS:
        if not (current < version <= target):
            continue
        checksum = hashlib.sha256(sql_up.encode("utf-8")).hexdigest()
        logger.info("Applying migration %d: %s", version, description)
        try:
            conn.execute("BEGIN")
            for statement in _statements(sql_up):
                _execute_statement(conn, statement)
            conn.execute(
                f"INSERT OR REPLACE INTO {MIGRATIONS_TABLE} "
                "(version, description, checksum) VALUES (?, ?, ?)",
                (version, description, checksum),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Migration %d failed", version)
            raise

    _migrate_legacy_playcount(conn)
    _backfill_metadata_keys(conn)
    conn.commit()


def rollback(conn: sqlite3.Connection, target_version: int) -> None:
    ensure_migrations_table(conn)
    current = get_current_version(conn)
    if current <= target_version:
        return

    for version, description, _sql_up, sql_down in reversed(MIGRATIONS):
        if not (target_version < version <= current):
            continue
        logger.info("Rolling back migration %d: %s", version, description)
        try:
            conn.execute("BEGIN")
            for statement in _statements(sql_down):
                _execute_statement(conn, statement)
            conn.execute(
                f"DELETE FROM {MIGRATIONS_TABLE} WHERE version=?", (version,)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Rollback of migration %d failed", version)
            raise
