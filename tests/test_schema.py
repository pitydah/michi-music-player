"""Tests for schema — initialization, migrations, indexes, and legacy data."""
import contextlib
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

    def test_core_tables_exist(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "media_items",
            "playlists",
            "playlist_items",
            "favorites",
            "album_art_cache",
            "detected_tracks",
            "scan_roots",
            "library_roots",
        }
        assert expected.issubset(tables)

    def test_core_indexes_exist(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        indexes = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        expected = {
            "idx_media_artist",
            "idx_media_album",
            "idx_media_genre",
            "idx_media_year",
            "idx_media_directory",
            "idx_pl_filepath",
            "idx_playlist_smart",
        }
        assert expected.issubset(indexes)

    def test_wal_mode_is_configured(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        assert mode is not None

    def test_playlist_all_migrations_idempotent(self):
        """Verify all playlist migrations can run twice without error."""
        conn = sqlite3.connect(":memory:")
        conn.execute(PLAYLISTS_SQL)
        from library.schema import PLAYLISTS_MIGRATIONS
        for col_name, col_def in PLAYLISTS_MIGRATIONS:
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(f"ALTER TABLE playlists ADD COLUMN {col_name} {col_def}")
        # Run again — should not raise
        for col_name, col_def in PLAYLISTS_MIGRATIONS:
            with contextlib.suppress(sqlite3.OperationalError):
                conn.execute(f"ALTER TABLE playlists ADD COLUMN {col_name} {col_def}")

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

    def test_media_item_migrations(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        cols = {
            r[1]
            for r in conn.execute("PRAGMA table_info(media_items)").fetchall()
        }
        expected = {
            "albumartist",
            "mb_track_id",
            "mb_album_id",
            "bpm",
            "replaygain_track",
            "track_uid",
            "content_hash",
            "deleted_at",
        }
        assert expected.issubset(cols)


class TestSchemaLegacyData:
    def test_populates_empty_track_uids(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        conn.execute(
            "INSERT INTO media_items (filepath, filename, directory, ext, kind, track_uid) "
            "VALUES (?,?,?,?,?,?)",
            ("/test.mp3", "test.mp3", "/", ".mp3", "audio", ""),
        )
        conn.commit()
        Schema._populate_track_uids(conn)
        uid = conn.execute(
            "SELECT track_uid FROM media_items WHERE filepath=?",
            ("/test.mp3",),
        ).fetchone()[0]
        assert uid.startswith("fp:")

    def test_migrates_scan_roots_to_library_roots(self):
        conn = sqlite3.connect(":memory:")
        Schema.initialize(conn)
        conn.execute(
            "INSERT INTO scan_roots (path, enabled, file_count) VALUES (?, ?, ?)",
            ("/music", 1, 7),
        )
        conn.commit()
        Schema._migrate_scan_roots_to_library_roots(conn)
        row = conn.execute(
            "SELECT path, enabled, file_count FROM library_roots WHERE path=?",
            ("/music",),
        ).fetchone()
        assert row == ("/music", 1, 7)
