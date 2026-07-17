"""Test migration system with various database states."""
import sqlite3
from library.migrations import migrate, get_current_version, ensure_migrations_table


def test_empty_db():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert get_current_version(conn) == 3
    conn.close()


def test_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    migrate(conn)  # second call should not fail
    assert get_current_version(conn) == 3
    conn.close()


def test_rollback():
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    assert get_current_version(conn) == 3
    # Verify tables exist
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "songs" in tables
    assert "albums" in tables
    conn.close()


def test_partial_migration():
    """Test migrating from a database that has only some columns."""
    conn = sqlite3.connect(":memory:")
    # Create schema manually (version 1)
    conn.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, filepath TEXT UNIQUE);
        CREATE TABLE albums (id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE artists (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
    """)
    ensure_migrations_table(conn)
    conn.execute("INSERT INTO _migrations (version, description) VALUES (1, 'manual')")
    conn.commit()

    migrate(conn)
    assert get_current_version(conn) == 3
    conn.close()
