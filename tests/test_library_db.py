import tempfile
import os
import sqlite3

from library.library_db import LibraryDB


class TestLibraryDB:
    def test_create_in_memory(self):
        db = LibraryDB(":memory:")
        assert db is not None

    def test_create_temp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            db = LibraryDB(path)
            assert db.conn is not None
        finally:
            os.unlink(path)

    def test_fts_is_initialized_lazily_on_first_search_access(self):
        db = LibraryDB(":memory:")

        before = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE name='media_fts'"
        ).fetchone()
        connection = db.conn
        after = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='media_fts'"
        ).fetchone()

        assert before is None
        assert connection is db._conn
        assert after == ("media_fts",)

    def test_fts_triggers_incrementally_sync_insert_update_and_delete(self):
        db = LibraryDB(":memory:")
        db.search_advanced("missing")

        cursor = db.conn.execute(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title, artist) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("/music/one.flac", "one.flac", "/music", ".flac", "audio", "First", "Artist"),
        )
        track_id = cursor.lastrowid
        assert db.conn.execute(
            "SELECT rowid FROM media_fts WHERE media_fts MATCH 'First'"
        ).fetchall() == [(track_id,)]

        db.conn.execute("UPDATE media_items SET title='Second' WHERE id=?", (track_id,))
        assert db.conn.execute(
            "SELECT rowid FROM media_fts WHERE media_fts MATCH 'First'"
        ).fetchall() == []
        assert db.conn.execute(
            "SELECT rowid FROM media_fts WHERE media_fts MATCH 'Second'"
        ).fetchall() == [(track_id,)]

        db.conn.execute("DELETE FROM media_items WHERE id=?", (track_id,))
        assert db.conn.execute(
            "SELECT rowid FROM media_fts WHERE media_fts MATCH 'Second'"
        ).fetchall() == []

    def test_fts_rebuild_runs_only_when_schema_changes(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as file:
            path = file.name
        try:
            db = LibraryDB(path)
            db._ensure_fts()
            statements = []
            db._conn.set_trace_callback(statements.append)

            db._ensure_fts()

            assert not any("VALUES('rebuild')" in statement for statement in statements)
            db.close()

            connection = sqlite3.connect(path)
            connection.executescript(
                "DROP TRIGGER media_items_fts_insert;"
                "DROP TRIGGER media_items_fts_update;"
                "DROP TRIGGER media_items_fts_delete;"
            )
            connection.close()

            reopened = LibraryDB(path)
            statements.clear()
            reopened._conn.set_trace_callback(statements.append)
            reopened._ensure_fts()

            assert any("VALUES('rebuild')" in statement for statement in statements)
            reopened.close()
        finally:
            os.unlink(path)

    def test_fetch_track_context_returns_persisted_metadata(self):
        db = LibraryDB(":memory:")
        db._conn.execute(
            "INSERT INTO media_items "
            "(filepath, filename, directory, ext, kind, title, artist, album, "
            " album_key, track_uid, year, genre, duration, format, "
            " sample_rate, bit_depth, bitrate) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("/music/one.flac", "one.flac", "/music", ".flac", "audio",
             "First", "Artist", "Album", "akey", "uid1", 1971, "Prog", 240.0,
             "flac", 44100, 16, 1411),
        )
        db._conn.commit()

        ctx = db.fetch_track_context("/music/one.flac")
        assert ctx["title"] == "First"
        assert ctx["artist"] == "Artist"
        assert ctx["album"] == "Album"
        assert ctx["album_key"] == "akey"
        assert ctx["track_uid"] == "uid1"
        assert ctx["year"] == 1971
        assert ctx["duration"] == 240.0
        assert ctx["format"] == "flac"
        assert ctx["sample_rate"] == 44100
        assert ctx["bit_depth"] == 16
        assert ctx["bitrate"] == 1411

    def test_fetch_track_context_empty_for_missing_filepath(self):
        db = LibraryDB(":memory:")
        assert db.fetch_track_context("/nope.flac") == {}
        assert db.fetch_track_context("") == {}

    def test_fetch_track_context_skips_soft_deleted(self):
        db = LibraryDB(":memory:")
        db._conn.execute(
            "INSERT INTO media_items (filepath, filename, directory, ext, kind, "
            "title, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("/music/gone.flac", "gone.flac", "/music", ".flac", "audio",
             "Gone", 1234567890),
        )
        db._conn.commit()
        assert db.fetch_track_context("/music/gone.flac") == {}
