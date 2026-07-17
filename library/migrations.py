"""Formal database migration system with versioning, transactions, and rollback."""
import logging
import sqlite3

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "_migrations"

# Each migration: (version, description, sql_up, sql_down)
MIGRATIONS = [
    (1, "Initial schema", """
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT DEFAULT '',
            album TEXT DEFAULT '',
            filepath TEXT UNIQUE NOT NULL,
            duration REAL DEFAULT 0,
            bitrate INTEGER DEFAULT 0,
            samplerate INTEGER DEFAULT 0,
            channels INTEGER DEFAULT 2,
            genre TEXT DEFAULT '',
            year INTEGER DEFAULT 0,
            track_number INTEGER DEFAULT 0,
            disc_number INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            playcount INTEGER DEFAULT 0,
            last_played TEXT DEFAULT '',
            date_added TEXT DEFAULT (datetime('now')),
            date_modified TEXT DEFAULT (datetime('now')),
            favorite INTEGER DEFAULT 0,
            format TEXT DEFAULT '',
            has_coverart INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            year INTEGER DEFAULT 0,
            cover_path TEXT DEFAULT '',
            track_count INTEGER DEFAULT 0,
            duration REAL DEFAULT 0,
            album_artist TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            bio TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            album_count INTEGER DEFAULT 0,
            track_count INTEGER DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS songs_fts USING fts5(
            title, artist, album, genre, content='songs', content_rowid='id'
        );
    """, """
        DROP TABLE IF EXISTS songs_fts;
        DROP TABLE IF EXISTS songs;
        DROP TABLE IF EXISTS albums;
        DROP TABLE IF EXISTS artists;
    """),
    (2, "Add track_uid and content_hash", """
        ALTER TABLE songs ADD COLUMN track_uid TEXT DEFAULT '';
        ALTER TABLE songs ADD COLUMN content_hash TEXT DEFAULT '';
    """, """
        ALTER TABLE songs DROP COLUMN track_uid;
        ALTER TABLE songs DROP COLUMN content_hash;
    """),
    (3, "Add deleted_at and scan_status", """
        ALTER TABLE songs ADD COLUMN deleted_at TEXT DEFAULT NULL;
        ALTER TABLE songs ADD COLUMN scan_status TEXT DEFAULT 'active';
        CREATE INDEX IF NOT EXISTS idx_songs_scan_status ON songs(scan_status);
    """, """
        DROP INDEX IF EXISTS idx_songs_scan_status;
        ALTER TABLE songs DROP COLUMN deleted_at;
        ALTER TABLE songs DROP COLUMN scan_status;
    """),
]


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get current migration version from database."""
    cursor = conn.execute(f"SELECT MAX(version) FROM {MIGRATIONS_TABLE}")
    row = cursor.fetchone()
    return row[0] if row and row[0] else 0


def ensure_migrations_table(conn: sqlite3.Connection):
    """Create migrations tracking table if not exists."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT DEFAULT (datetime('now')),
            checksum TEXT DEFAULT ''
        )
    """)


def migrate(conn: sqlite3.Connection, target_version: int | None = None, backup_path: str | None = None):
    """Run migrations up to target_version (or latest if None)."""
    ensure_migrations_table(conn)
    current = get_current_version(conn)

    if backup_path:
        logger.info(f"Backing up database to {backup_path}")
        conn.execute(f"VACUUM INTO '{backup_path}'")

    target = target_version or max(m[0] for m in MIGRATIONS)

    if current >= target:
        logger.info(f"Database already at version {current} (target: {target})")
        return

    for version, description, sql_up, _sql_down in MIGRATIONS:
        if version > current and version <= target:
            logger.info(f"Applying migration {version}: {description}")
            try:
                conn.executescript(sql_up)
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
    """Rollback migrations to target_version."""
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
