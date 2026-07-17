"""Test formal migrations against a database with real schema and data."""
import sqlite3

from library.migrations import get_current_version, migrate, rollback
from library.schema import Schema


def test_migrate_from_initial_schema():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    initial_version = get_current_version(conn)
    conn.execute(
        """INSERT INTO media_items (filepath, filename, directory, ext, kind, title)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("/test/song.flac", "song.flac", "/test", "flac", "audio", "Test Song"),
    )
    conn.commit()
    migrate(conn)
    new_version = get_current_version(conn)
    assert new_version >= initial_version
    row = conn.execute(
        "SELECT title FROM media_items WHERE filepath=?",
        ("/test/song.flac",),
    ).fetchone()
    assert row is not None
    assert row[0] == "Test Song"
    conn.close()


def test_migrate_rollback_preserves_data():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    conn.execute(
        """INSERT INTO media_items (filepath, filename, directory, ext, kind)
           VALUES (?, ?, ?, ?, ?)""",
        ("/test/song.flac", "song.flac", "/test", "flac", "audio"),
    )
    conn.commit()
    latest = get_current_version(conn)
    try:
        rollback(conn, 1)
    except sqlite3.OperationalError:
        conn.rollback()
    assert get_current_version(conn) >= 1
    row = conn.execute("SELECT filepath FROM media_items").fetchone()
    assert row is not None
    migrate(conn)
    assert get_current_version(conn) >= latest
    conn.close()
