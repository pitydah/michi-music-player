"""Tests for versioned, idempotent catalogue migrations."""
import sqlite3

from library.migrations import ensure_migrations_table, get_current_version, migrate

LATEST_VERSION = 6


def test_empty_db():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert get_current_version(conn) == LATEST_VERSION
    conn.close()


def test_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    migrate(conn)
    assert get_current_version(conn) == LATEST_VERSION
    conn.close()


def test_latest_schema_contains_normalized_metadata_columns():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(media_items)")}
    assert {
        "normalized_title",
        "normalized_artist",
        "normalized_album",
        "normalized_albumartist",
        "metadata_source",
        "metadata_confidence",
        "metadata_completeness",
        "metadata_issues",
        "metadata_hash",
    }.issubset(columns)
    conn.close()


def test_latest_schema_contains_library_indexes():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    indexes = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert {
        "idx_media_active_norm_title",
        "idx_media_active_norm_artist_album",
        "idx_media_active_album_tracks",
        "idx_media_metadata_health",
        "idx_play_history_track_time",
    }.issubset(indexes)
    conn.close()


def test_rollback_keeps_initial_catalogue_tables():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"media_items", "playlists", "play_history"}.issubset(tables)
    conn.close()


def test_partial_migration_skips_existing_columns():
    """A valid v1 catalogue may already contain a later backported column."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY,
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
            date_added REAL,
            track_uid TEXT DEFAULT ''
        );
        CREATE TABLE playlists (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE play_history (
            track_id TEXT NOT NULL,
            played_at REAL DEFAULT 0
        );
        CREATE TABLE favorites (track_id TEXT NOT NULL UNIQUE);
    """)
    ensure_migrations_table(conn)
    conn.execute(
        "INSERT INTO _migrations (version, description) VALUES (1, 'manual')"
    )
    conn.commit()

    migrate(conn)
    assert get_current_version(conn) == LATEST_VERSION
    columns = {row[1] for row in conn.execute("PRAGMA table_info(media_items)")}
    assert {"track_uid", "content_hash", "metadata_hash"}.issubset(columns)
    conn.close()


def test_backfills_normalized_metadata_for_existing_rows():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    conn.execute(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "/music/01.mp3",
            "01.mp3",
            "/music",
            ".mp3",
            "audio",
            "Canción Única",
            "Árbol Azul",
            "Disco Ñ",
        ),
    )
    conn.execute(
        "UPDATE media_items SET normalized_title='', metadata_hash=''"
    )
    conn.execute("DELETE FROM _migrations WHERE version=6")
    conn.commit()

    migrate(conn)
    row = conn.execute(
        "SELECT normalized_title, normalized_artist, metadata_hash, "
        "metadata_completeness FROM media_items"
    ).fetchone()
    assert row[0] == "cancion unica"
    assert row[1] == "arbol azul"
    assert len(row[2]) == 64
    assert row[3] > 0
    conn.close()
