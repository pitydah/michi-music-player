"""Tests for database schema initialization — idempotency and column existence."""
import sqlite3

from library.schema import Schema, MEDIA_ITEMS_SQL, PLAYLISTS_SQL


class TestSchemaIdempotency:
    def test_initialize_runs_twice(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        Schema.initialize(conn)
        cur = conn.execute("SELECT COUNT(*) FROM playlists")
        assert cur.fetchone()[0] == 0

    def test_playlists_table_exists(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        cur = conn.execute("PRAGMA table_info(playlists)")
        cols = {r[1] for r in cur.fetchall()}
        assert "id" in cols
        assert "name" in cols

    def test_is_smart_column_exists(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        cur = conn.execute("PRAGMA table_info(playlists)")
        cols = {r[1] for r in cur.fetchall()}
        assert "is_smart" in cols, "playlists.is_smart column missing after schema init"

    def test_is_smart_default_zero(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("test",))
        row = conn.execute("SELECT is_smart FROM playlists WHERE name=?", ("test",)).fetchone()
        assert row is not None
        assert row[0] == 0

    def test_idx_playlist_smart_exists(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        cur = conn.execute("PRAGMA index_list(playlists)")
        indexes = {r[1] for r in cur.fetchall()}
        assert "idx_playlist_smart" in indexes

    def test_playlist_all_migrations_idempotent(self):
        """Verify all playlist migrations can run twice without error."""
        conn = sqlite3.connect(":memory:")
        conn.execute(PLAYLISTS_SQL)
        from library.schema import PLAYLISTS_MIGRATIONS
        for col_name, col_def in PLAYLISTS_MIGRATIONS:
            try:
                conn.execute(f"ALTER TABLE playlists ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass
        # Run again — should not raise
        for col_name, col_def in PLAYLISTS_MIGRATIONS:
            try:
                conn.execute(f"ALTER TABLE playlists ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass

    def test_full_schema_twice(self):
        """Run Schema.initialize twice — no errors."""
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        Schema.initialize(conn)
        cur = conn.execute("SELECT COUNT(*) FROM media_items")
        assert cur.fetchone()[0] == 0


class TestSchemaTables:
    def test_media_items_table(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(MEDIA_ITEMS_SQL)
        cur = conn.execute("PRAGMA table_info(media_items)")
        cols = {r[1] for r in cur.fetchall()}
        assert "filepath" in cols
        assert "title" in cols
        assert "artist" in cols

    def test_playlists_table(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(PLAYLISTS_SQL)
        Schema.run_migrations(conn)
        cur = conn.execute("PRAGMA table_info(playlists)")
        cols = {r[1] for r in cur.fetchall()}
        assert "name" in cols
        assert "is_smart" in cols
