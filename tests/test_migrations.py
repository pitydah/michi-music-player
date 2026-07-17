"""Test migration system with various database states."""
import sqlite3
from library.migrations import migrate, get_current_version, ensure_migrations_table


def test_empty_db():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert get_current_version(conn) == 5
    conn.close()


def test_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    migrate(conn)  # second call should not fail
    assert get_current_version(conn) == 5
    conn.close()


def test_rollback():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert get_current_version(conn) == 5
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "media_items" in tables
    assert "playlists" in tables
    assert "play_history" in tables
    conn.close()


def test_partial_migration():
    """Test migrating from a database that has only some columns."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT UNIQUE,
            filename TEXT, directory TEXT, ext TEXT, kind TEXT);
        CREATE TABLE playlists (id INTEGER PRIMARY KEY, name TEXT);
    """)
    ensure_migrations_table(conn)
    conn.execute("INSERT INTO _migrations (version, description) VALUES (1, 'manual')")
    conn.commit()

    migrate(conn)
    assert get_current_version(conn) == 5
    # Verify v2 columns were added
    cursor = conn.execute("PRAGMA table_info(media_items)")
    cols = {r[1] for r in cursor.fetchall()}
    assert "track_uid" in cols
    assert "content_hash" in cols
    conn.close()
