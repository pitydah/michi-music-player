"""Formal database migration system with versioning, transactions, and rollback.

Uses the real schema tables from library/schema.py.
"""
import logging
import sqlite3

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "_migrations"

# Each migration: (version, description, sql_up, sql_down)
# Version 1 corresponds to the schema created by Schema.initialize() in schema.py
MIGRATIONS = [
    (1, "Initial schema", """
        CREATE TABLE IF NOT EXISTS media_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath    TEXT UNIQUE NOT NULL,
            filename    TEXT NOT NULL,
            directory   TEXT NOT NULL,
            ext         TEXT NOT NULL,
            kind        TEXT NOT NULL,
            size        INTEGER,
            mtime       REAL,
            duration    REAL,
            channels    INTEGER,
            sample_rate INTEGER,
            bitrate     INTEGER,
            title       TEXT,
            artist      TEXT,
            album       TEXT,
            year        INTEGER,
            genre       TEXT,
            track_number INTEGER,
            composer    TEXT,
            date_added  REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlists (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cover_path TEXT DEFAULT '',
            cover_type TEXT DEFAULT 'mosaic',
            description TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath    TEXT NOT NULL,
            track_id    INTEGER REFERENCES media_items(id),
            position    INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY,
            filepath TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id   TEXT NOT NULL,
            device     TEXT DEFAULT 'desktop',
            played_at  REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE,
            device   TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS album_art_cache (
            album_hash TEXT PRIMARY KEY,
            mime       TEXT,
            data       BLOB
        );
        CREATE TABLE IF NOT EXISTS detected_tracks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT NOT NULL,
            artist    TEXT NOT NULL,
            album     TEXT,
            year      INTEGER,
            genre     TEXT,
            duration  REAL,
            source    TEXT DEFAULT '',
            provider  TEXT DEFAULT '',
            confidence REAL,
            isrc      TEXT,
            artwork_url TEXT,
            external_url TEXT,
            filepath  TEXT,
            matched_library_id INTEGER,
            raw_json  TEXT,
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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            path          TEXT UNIQUE NOT NULL,
            enabled       INTEGER DEFAULT 1,
            last_scan     REAL,
            file_count    INTEGER DEFAULT 0,
            added_count   INTEGER DEFAULT 0,
            updated_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            missing_count INTEGER DEFAULT 0,
            created_at    REAL DEFAULT (strftime('%s','now')),
            updated_at    REAL
        );
        CREATE TABLE IF NOT EXISTS track_genres (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id        INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
            genre           TEXT NOT NULL,
            canonical_genre TEXT NOT NULL DEFAULT '',
            original_value  TEXT NOT NULL DEFAULT '',
            confidence      REAL DEFAULT 1.0,
            source          TEXT DEFAULT 'tag',
            is_manual       INTEGER DEFAULT 0,
            created_at      REAL DEFAULT (strftime('%s','now')),
            updated_at      REAL,
            UNIQUE(track_id, genre)
        );
        CREATE TABLE IF NOT EXISTS genre_aliases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            alias           TEXT NOT NULL UNIQUE,
            canonical_genre TEXT NOT NULL,
            confidence      REAL DEFAULT 1.0,
            source          TEXT DEFAULT 'builtin',
            is_builtin      INTEGER DEFAULT 0,
            is_user_defined INTEGER DEFAULT 0,
            created_at      REAL DEFAULT (strftime('%s','now')),
            updated_at      REAL
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
    (2, "Add track_uid and content_hash to media_items", """
        ALTER TABLE media_items ADD COLUMN track_uid TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN content_hash TEXT DEFAULT '';
    """, """
        ALTER TABLE media_items DROP COLUMN track_uid;
        ALTER TABLE media_items DROP COLUMN content_hash;
    """),
    (3, "Add mtime_processed, file_size, and format to media_items", """
        ALTER TABLE media_items ADD COLUMN mtime_processed REAL DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN file_size INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN format TEXT DEFAULT '';
    """, """
        ALTER TABLE media_items DROP COLUMN mtime_processed;
        ALTER TABLE media_items DROP COLUMN file_size;
        ALTER TABLE media_items DROP COLUMN format;
    """),
    (4, "Add albumartist and disc_number to media_items", """
        ALTER TABLE media_items ADD COLUMN albumartist TEXT DEFAULT '';
        ALTER TABLE media_items ADD COLUMN disc_number INTEGER DEFAULT 0;
    """, """
        ALTER TABLE media_items DROP COLUMN albumartist;
        ALTER TABLE media_items DROP COLUMN disc_number;
    """),
    (5, "Add rating and playcount to media_items", """
        ALTER TABLE media_items ADD COLUMN rating INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN playcount INTEGER DEFAULT 0;
        ALTER TABLE media_items ADD COLUMN last_played TEXT DEFAULT '';
    """, """
        ALTER TABLE media_items DROP COLUMN last_played;
        ALTER TABLE media_items DROP COLUMN playcount;
        ALTER TABLE media_items DROP COLUMN rating;
    """),
]


def get_current_version(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(f"SELECT MAX(version) FROM {MIGRATIONS_TABLE}")
    row = cursor.fetchone()
    return row[0] if row and row[0] else 0


def ensure_migrations_table(conn: sqlite3.Connection):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT DEFAULT (datetime('now')),
            checksum TEXT DEFAULT ''
        )
    """)


def migrate(conn: sqlite3.Connection, target_version: int | None = None, backup_path: str | None = None):
    ensure_migrations_table(conn)
    current = get_current_version(conn)

    if backup_path:
        logger.info(f"Backing up database to {backup_path}")
        conn.execute(f"VACUUM INTO '{backup_path}'")

    target = target_version or max(m[0] for m in MIGRATIONS)

    if current >= target:
        logger.info(f"Database already at version {current} (target: {target})")
        return

    def _exec_migration_safe(conn, sql_block):
        """Execute SQL block statement by statement, skipping ALTER ADD COLUMN if column exists."""
        for statement in sql_block.strip().split(';'):
            stmt = statement.strip()
            if not stmt:
                continue
            # For ALTER TABLE ADD COLUMN, check if column exists first
            if stmt.upper().startswith('ALTER TABLE') and 'ADD COLUMN' in stmt.upper():
                import re
                m = re.search(r'ALTER TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)', stmt, re.IGNORECASE)
                if m:
                    table, col = m.group(1), m.group(2)
                    cursor = conn.execute(f"PRAGMA table_info({table})")
                    existing = {r[1] for r in cursor.fetchall()}
                    if col in existing:
                        logger.debug(f"Column {table}.{col} already exists, skipping")
                        continue
            try:
                conn.execute(stmt)
            except Exception as e:
                logger.warning(f"Statement skipped (non-fatal): {e}")
                conn.rollback()
                conn.execute("ROLLBACK")

    for version, description, sql_up, _sql_down in MIGRATIONS:
        if version > current and version <= target:
            logger.info(f"Applying migration {version}: {description}")
            try:
                conn.execute("BEGIN")
                _exec_migration_safe(conn, sql_up)
                conn.execute(f"""
                    INSERT OR REPLACE INTO {MIGRATIONS_TABLE} (version, description)
                    VALUES (?, ?)
                """, (version, description))
                conn.commit()
                logger.info(f"Migration {version} applied successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Migration {version} failed: {e}")
                raise


def rollback(conn: sqlite3.Connection, target_version: int):
    ensure_migrations_table(conn)
    current = get_current_version(conn)

    if current <= target_version:
        return

    for version, description, _sql_up, sql_down in reversed(MIGRATIONS):
        if version > target_version and version <= current:
            logger.info(f"Rolling back migration {version}: {description}")
            try:
                conn.executescript(sql_down)
                conn.execute(f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = ?", (version,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Rollback of migration {version} failed: {e}")
                raise
