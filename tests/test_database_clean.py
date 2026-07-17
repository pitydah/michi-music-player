"""Test that a clean database initializes and migrations run correctly."""
import sqlite3
from library.schema import Schema


def test_clean_db_creates_tables():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    Schema.initialize(conn)

    expected_tables = {
        "media_items", "playlists", "playlist_items",
        "queue_state", "play_history", "favorites",
        "album_art_cache", "detected_tracks",
        "scan_roots", "index_errors", "library_roots",
        "track_genres", "genre_aliases", "genre_stats_cache",
        "genre_cleanup_suggestions", "genre_operation_log",
    }
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    actual = {r[0] for r in cursor.fetchall()}
    missing = expected_tables - actual
    assert not missing, f"Missing tables: {missing}"
    conn.close()


def test_migrations_run_clean():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    Schema.initialize(conn)
    Schema.run_migrations(conn)

    cursor = conn.execute("PRAGMA table_info(media_items)")
    cols = {r[1] for r in cursor.fetchall()}
    assert "track_uid" in cols
    assert "content_hash" in cols
    assert "deleted_at" in cols
    assert "scan_status" in cols
    conn.close()


def test_fts5_available():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
    conn.execute("INSERT INTO test_fts(content) VALUES ('test')")
    result = conn.execute(
        "SELECT * FROM test_fts WHERE test_fts MATCH 'test'"
    ).fetchone()
    assert result is not None
    conn.close()
