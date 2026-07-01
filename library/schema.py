"""Schema — all CREATE TABLE statements, indexes, and migrations.

Extracted from library_db.py for clarity and maintainability.
The Schema class is consumed by LibraryDB.__init__ to set up the database.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import sqlite3

logger = logging.getLogger("michi.schema")

# ── TABLE SQL ──

MEDIA_ITEMS_SQL = """CREATE TABLE IF NOT EXISTS media_items (
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
)"""

PLAYLISTS_SQL = """CREATE TABLE IF NOT EXISTS playlists (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cover_path TEXT DEFAULT '',
    cover_type TEXT DEFAULT 'mosaic',
    description TEXT DEFAULT '',
    created_at REAL DEFAULT (strftime('%s','now'))
)"""

PLAYLIST_ITEMS_SQL = """CREATE TABLE IF NOT EXISTS playlist_items (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id),
    filepath    TEXT NOT NULL,
    track_id    INTEGER REFERENCES media_items(id),
    position    INTEGER DEFAULT 0
)"""

QUEUE_STATE_SQL = """CREATE TABLE IF NOT EXISTS queue_state (
    id INTEGER PRIMARY KEY,
    filepath TEXT NOT NULL
)"""

PLAY_HISTORY_SQL = """CREATE TABLE IF NOT EXISTS play_history (
    track_id   TEXT NOT NULL,
    device     TEXT DEFAULT 'desktop',
    played_at  REAL DEFAULT (strftime('%s','now'))
)"""

FAVORITES_SQL = """CREATE TABLE IF NOT EXISTS favorites (
    track_id TEXT NOT NULL UNIQUE,
    device   TEXT DEFAULT 'desktop',
    added_at REAL DEFAULT (strftime('%s','now'))
)"""

ALBUM_ART_CACHE_SQL = """CREATE TABLE IF NOT EXISTS album_art_cache (
    album_hash TEXT PRIMARY KEY,
    mime       TEXT,
    data       BLOB
)"""

DETECTED_TRACKS_SQL = """CREATE TABLE IF NOT EXISTS detected_tracks (
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
)"""

SCAN_ROOTS_SQL = """CREATE TABLE IF NOT EXISTS scan_roots (
    path TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 1,
    last_scan_started REAL,
    last_scan_finished REAL,
    file_count INTEGER DEFAULT 0,
    added_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0
)"""

INDEX_ERRORS_SQL = """CREATE TABLE IF NOT EXISTS index_errors (
    filepath TEXT,
    error TEXT,
    stage TEXT,
    updated_at REAL DEFAULT (strftime('%s','now'))
)"""

LIBRARY_ROOTS_SQL = """CREATE TABLE IF NOT EXISTS library_roots (
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
)"""

# ── Genre tables ──

TRACK_GENRES_SQL = """CREATE TABLE IF NOT EXISTS track_genres (
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
)"""

GENRE_ALIASES_SQL = """CREATE TABLE IF NOT EXISTS genre_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alias           TEXT NOT NULL UNIQUE,
    canonical_genre TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,
    source          TEXT DEFAULT 'builtin',
    is_builtin      INTEGER DEFAULT 0,
    is_user_defined INTEGER DEFAULT 0,
    created_at      REAL DEFAULT (strftime('%s','now')),
    updated_at      REAL
)"""

GENRE_STATS_CACHE_SQL = """CREATE TABLE IF NOT EXISTS genre_stats_cache (
    genre               TEXT PRIMARY KEY,
    canonical_genre     TEXT NOT NULL DEFAULT '',
    track_count         INTEGER DEFAULT 0,
    album_count         INTEGER DEFAULT 0,
    artist_count        INTEGER DEFAULT 0,
    duration_total      REAL DEFAULT 0.0,
    dominant_format     TEXT DEFAULT '',
    dominant_quality    TEXT DEFAULT '',
    lossless_count      INTEGER DEFAULT 0,
    lossy_count         INTEGER DEFAULT 0,
    hires_count         INTEGER DEFAULT 0,
    missing_metadata_count INTEGER DEFAULT 0,
    play_count          INTEGER DEFAULT 0,
    favorite_count      INTEGER DEFAULT 0,
    year_min            INTEGER DEFAULT 0,
    year_max            INTEGER DEFAULT 0,
    dominant_decade     TEXT DEFAULT '',
    health_status       TEXT DEFAULT 'ok',
    last_computed_at    REAL DEFAULT 0
)"""

GENRE_CLEANUP_SUGGESTIONS_SQL = """CREATE TABLE IF NOT EXISTS genre_cleanup_suggestions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_type     TEXT NOT NULL,
    source_genre        TEXT NOT NULL,
    target_genre        TEXT DEFAULT '',
    affected_track_count INTEGER DEFAULT 0,
    confidence          REAL DEFAULT 0.0,
    reason              TEXT DEFAULT '',
    status              TEXT DEFAULT 'pending',
    extra_json          TEXT DEFAULT '{}',
    created_at          REAL DEFAULT (strftime('%s','now')),
    resolved_at         REAL
)"""

GENRE_OPERATION_LOG_SQL = """CREATE TABLE IF NOT EXISTS genre_operation_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type  TEXT NOT NULL,
    source_genre    TEXT DEFAULT '',
    target_genre    TEXT DEFAULT '',
    track_ids       TEXT DEFAULT '',
    affected_count  INTEGER DEFAULT 0,
    wrote_tags      INTEGER DEFAULT 0,
    details_json    TEXT DEFAULT '{}',
    created_at      REAL DEFAULT (strftime('%s','now'))
)"""

# ── INDEX SQL ──

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_pl_filepath ON playlist_items(filepath)",
    "CREATE INDEX IF NOT EXISTS idx_pl_playlist ON playlist_items(playlist_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_pl_unique_track "
    "ON playlist_items(playlist_id, track_id) WHERE track_id IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_pl_position ON playlist_items(playlist_id, position)",

    "CREATE INDEX IF NOT EXISTS idx_detected_tracks_time ON detected_tracks(detected_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_detected_tracks_artist_title ON detected_tracks(artist, title)",
    "CREATE INDEX IF NOT EXISTS idx_media_artist ON media_items(artist)",
    "CREATE INDEX IF NOT EXISTS idx_media_album ON media_items(album)",
    "CREATE INDEX IF NOT EXISTS idx_media_directory ON media_items(directory)",
    "CREATE INDEX IF NOT EXISTS idx_media_genre ON media_items(genre)",
    "CREATE INDEX IF NOT EXISTS idx_media_year ON media_items(year)",
]

GENRE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_track_genres_track ON track_genres(track_id)",
    "CREATE INDEX IF NOT EXISTS idx_track_genres_genre ON track_genres(canonical_genre)",
    "CREATE INDEX IF NOT EXISTS idx_genre_aliases_canonical ON genre_aliases(canonical_genre)",
    "CREATE INDEX IF NOT EXISTS idx_genre_suggestions_status ON genre_cleanup_suggestions(status)",
    "CREATE INDEX IF NOT EXISTS idx_genre_suggestions_type ON genre_cleanup_suggestions(suggestion_type)",
]

# Extra indexes for columns added via migrations (not in CREATE TABLE)
_PLAYLIST_EXTRA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pl_added_at ON playlist_items(playlist_id, added_at)",
    "CREATE INDEX IF NOT EXISTS idx_pl_source ON playlist_items(source)",
    "CREATE INDEX IF NOT EXISTS idx_playlist_updated ON playlists(updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_playlist_sync ON playlists(sync_enabled, sync_status)",
    "CREATE INDEX IF NOT EXISTS idx_playlist_smart ON playlists(is_smart)",
]

# ── MIGRATION DEFINITIONS ──

MEDIA_ITEMS_MIGRATIONS = [
    ("year", "INTEGER"),
    ("genre", "TEXT"),
    ("track_number", "INTEGER"),
    ("composer", "TEXT"),
    ("albumartist", "TEXT"),
    ("disc_number", "INTEGER"),
    ("disc_total", "INTEGER"),
    ("track_total", "INTEGER"),
    ("mb_track_id", "TEXT"),
    ("mb_album_id", "TEXT"),
    ("mb_albumartist_id", "TEXT DEFAULT ''"),
    ("cover_hash", "TEXT"),       # DEPRECATED — never used, kept for compat
    ("rating", "INTEGER DEFAULT 0"),
    ("play_count", "INTEGER DEFAULT 0"),
    ("skip_count", "INTEGER DEFAULT 0"),  # DEPRECATED — never used, kept for compat
    ("last_played", "REAL"),
    ("bpm", "INTEGER"),
    ("replaygain_track", "REAL"),
    ("replaygain_album", "REAL"),
    ("bit_depth", "INTEGER DEFAULT 0"),
    ("isrc", "TEXT DEFAULT ''"),
    ("label", "TEXT DEFAULT ''"),
    ("conductor", "TEXT DEFAULT ''"),
    ("compilation", "INTEGER DEFAULT 0"),
    ("media_type", "TEXT DEFAULT ''"),
    ("encoder", "TEXT DEFAULT ''"),
    ("copyright", "TEXT DEFAULT ''"),
    ("originaldate", "TEXT DEFAULT ''"),
    ("remixer", "TEXT DEFAULT ''"),
    ("grouping", "TEXT DEFAULT ''"),
    ("mood", "TEXT DEFAULT ''"),
    ("replaygain_track_peak", "REAL"),
    ("content_hash", "TEXT DEFAULT ''"),
    ("track_uid", "TEXT DEFAULT ''"),
    ("file_hash", "TEXT DEFAULT ''"),
    ("metadata_hash", "TEXT DEFAULT ''"),
    ("created_at", "REAL DEFAULT (strftime('%s','now'))"),
    ("updated_at", "REAL"),
    ("deleted_at", "REAL"),
    ("last_scanned", "REAL"),
    ("scan_status", "TEXT DEFAULT 'ok'"),
    ("scan_error", "TEXT DEFAULT ''"),
    ("comment", "TEXT DEFAULT ''"),
    ("lyricist", "TEXT DEFAULT ''"),
    ("replaygain_album_peak", "REAL"),
    ("r128_track_gain", "REAL"),
    ("r128_album_gain", "REAL"),
    ("mb_artist_id", "TEXT DEFAULT ''"),
    ("mb_releasegroup_id", "TEXT DEFAULT ''"),
    ("acoustid_id", "TEXT DEFAULT ''"),
    ("acoustid_fingerprint", "TEXT DEFAULT ''"),
    ("key", "TEXT DEFAULT ''"),
    ("quality", "TEXT DEFAULT ''"),
    ("analysis_status", "TEXT DEFAULT ''"),
    ("spectral_verdict", "TEXT DEFAULT ''"),
]

PLAYLISTS_MIGRATIONS = [
     ("cover_path", "TEXT DEFAULT ''"),
     ("cover_type", "TEXT DEFAULT 'mosaic'"),
     ("description", "TEXT DEFAULT ''"),
     ("created_at", "REAL DEFAULT (strftime('%s','now'))"),
     ("rules_json", "TEXT DEFAULT ''"),
     ("updated_at", "REAL"),
     ("last_played", "REAL"),
     ("sync_enabled", "INTEGER DEFAULT 0"),
     ("sync_status", "TEXT DEFAULT ''"),
     ("sync_version", "INTEGER DEFAULT 1"),
     ("is_smart", "INTEGER DEFAULT 0"),
     ("source", "TEXT DEFAULT 'local'"),
     ("locked", "INTEGER DEFAULT 0"),
     ("health_score", "INTEGER DEFAULT 100"),
     ("health_json", "TEXT DEFAULT ''"),
 ]

DETECTED_TRACKS_MIGRATIONS = [
    ("source_type", "TEXT DEFAULT ''"),
    ("source_label", "TEXT DEFAULT ''"),
    ("source_uri", "TEXT DEFAULT ''"),
    ("match_status", "TEXT DEFAULT ''"),
    ("matched_filepath", "TEXT DEFAULT ''"),
    ("provider_track_id", "TEXT DEFAULT ''"),
    ("provider_artist_id", "TEXT DEFAULT ''"),
    ("album_art_path", "TEXT DEFAULT ''"),
    ("latency_ms", "INTEGER DEFAULT 0"),
]

PLAYLIST_ITEMS_MIGRATIONS = [
     ("track_id", "INTEGER REFERENCES media_items(id)"),
     ("position", "INTEGER DEFAULT 0"),
     ("added_at", "REAL DEFAULT (strftime('%s','now'))"),
     ("source", "TEXT DEFAULT 'manual'"),
     ("sync_status", "TEXT DEFAULT ''"),
 ]

SCAN_ROOTS_MIGRATIONS = [
    ("created_at", "REAL DEFAULT (strftime('%s','now'))"),
    ("updated_at", "REAL"),
]


class Schema:
    """Database schema init — CREATE TABLE, indexes, and migrations."""

    @staticmethod
    def initialize(conn: sqlite3.Connection):
        conn.execute("PRAGMA journal_mode=WAL")
        for sql in [
            MEDIA_ITEMS_SQL, PLAYLISTS_SQL, PLAYLIST_ITEMS_SQL,
            QUEUE_STATE_SQL, PLAY_HISTORY_SQL, FAVORITES_SQL,
            ALBUM_ART_CACHE_SQL, DETECTED_TRACKS_SQL,
        ]:
            conn.execute(sql)
        conn.commit()

        for sql in INDEX_SQL[:5]:
            conn.execute(sql)
        conn.commit()

        Schema.run_migrations(conn)

        for sql in INDEX_SQL[5:]:
            conn.execute(sql)
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_albumartist ON media_items(albumartist)")
        conn.commit()

        for sql in [SCAN_ROOTS_SQL, INDEX_ERRORS_SQL, LIBRARY_ROOTS_SQL]:
            conn.execute(sql)
        conn.commit()

        # Genre tables
        for sql in [
            TRACK_GENRES_SQL, GENRE_ALIASES_SQL, GENRE_STATS_CACHE_SQL,
            GENRE_CLEANUP_SUGGESTIONS_SQL, GENRE_OPERATION_LOG_SQL,
        ]:
            conn.execute(sql)
        conn.commit()

        # Genre indexes (must run AFTER genre tables exist)
        for sql in GENRE_INDEX_SQL:
            conn.execute(sql)
        conn.commit()

        Schema.run_migrations(conn)
        Schema._migrate_scan_roots_to_library_roots(conn)
        Schema._populate_track_uids(conn)

    @staticmethod
    def run_migrations(conn: sqlite3.Connection):
        """Add missing columns to existing tables."""
        Schema._add_columns(conn, "media_items", MEDIA_ITEMS_MIGRATIONS)
        Schema._add_columns(conn, "playlists", PLAYLISTS_MIGRATIONS)
        Schema._add_columns(conn, "detected_tracks", DETECTED_TRACKS_MIGRATIONS)
        Schema._add_columns(conn, "playlist_items", PLAYLIST_ITEMS_MIGRATIONS)
        Schema._add_columns(conn, "scan_roots", SCAN_ROOTS_MIGRATIONS)

        # Populate track_id for existing playlist items
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("""
                UPDATE playlist_items SET track_id = (
                    SELECT m.id FROM media_items m WHERE m.filepath = playlist_items.filepath
                ) WHERE track_id IS NULL
            """)
        conn.commit()

        # Extra indexes for migration-only columns
        for idx in _PLAYLIST_EXTRA_INDEXES:
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(idx)

        # Track schema version
        new_ver = 4  # Bump when adding new migrations
        old_ver = conn.execute("PRAGMA user_version").fetchone()[0]
        if old_ver < new_ver:
            conn.execute(f"PRAGMA user_version={new_ver}")
            logger.info("Schema migrated: %d → %d", old_ver, new_ver)

    # ── Internal helpers ──

    @staticmethod
    def _add_columns(conn, table: str, columns: list[tuple[str, str]]):
        existing = {r[0] for r in conn.execute(
            f"PRAGMA table_info({table})").fetchall()}
        for col, col_def in columns:
            if col not in existing:
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")

    @staticmethod
    def _migrate_scan_roots_to_library_roots(conn: sqlite3.Connection):
        """Copy data from legacy scan_roots to library_roots (idempotent)."""
        try:
            existing = {r[0] for r in conn.execute(
                "SELECT path FROM library_roots").fetchall()}
        except sqlite3.OperationalError:
            return
        rows = conn.execute(
            "SELECT path, enabled, last_scan_started, last_scan_finished, "
            "file_count, added_count, updated_count, skipped_count, missing_count "
            "FROM scan_roots").fetchall()
        for (path, enabled, _started, finished,
             file_count, added, updated, skipped, missing) in rows:
            if path in existing:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO library_roots "
                "(path, enabled, last_scan, file_count, added_count, "
                "updated_count, skipped_count, missing_count, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (path, enabled, finished, file_count, added,
                 updated, skipped, missing, finished))
        conn.commit()

    @staticmethod
    def _populate_track_uids(conn: sqlite3.Connection):
        """Populate track_uid for existing rows where it was not computed."""
        cursor = conn.execute(
            "SELECT id, filepath, artist, album, title, duration, "
            "mb_track_id, mb_album_id "
            "FROM media_items WHERE track_uid = '' OR track_uid IS NULL")
        rows = cursor.fetchall()
        if not rows:
            return
        updates = []
        for rid, fp, artist, album, title, duration, mb_track, _mb_album in rows:
            uid = Schema._compute_track_uid(
                fp, artist, album, title, duration, mb_track)
            updates.append((uid, rid))
        conn.executemany(
            "UPDATE media_items SET track_uid=? WHERE id=?", updates)
        conn.commit()
        logger.info("Populated track_uid for %d records", len(updates))

    @staticmethod
    def _compute_track_uid(filepath: str, artist: str | None,
                           album: str | None, title: str | None,
                           duration: float, mb_track_id: str | None) -> str:
        if mb_track_id and mb_track_id.strip():
            return f"mb:{mb_track_id.strip()}"
        fp_hash = hashlib.sha256(filepath.encode()).hexdigest()[:16]
        return f"fp:{fp_hash}"
