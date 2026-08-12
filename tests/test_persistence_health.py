"""M11.2A persistence health detection tests — real SQLite + temp files."""

import json
import sqlite3
from pathlib import Path

from michi.domain.persistence_health import (
    PersistenceHealth,
)
from michi.domain.settings import SettingsState
from michi.infrastructure import sqlite_settings
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


class TestMissingDatabase:
    def test_missing_classified_and_not_created(self, tmp_path):
        db = tmp_path / "absent.db"
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MISSING
        assert db.exists() is False


class TestHealthyDatabase:
    def test_healthy(self, tmp_path):
        db = tmp_path / "healthy.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(volume=42, muted=True, last_directory="/m"))
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.HEALTHY

    def test_partial_settings_healthy(self, tmp_path):
        db = tmp_path / "partial.db"
        _write_raw_rows(db, [("volume", "42")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.HEALTHY

    def test_unknown_key_tolerated(self, tmp_path):
        db = tmp_path / "unknown.db"
        _write_raw_rows(db, [("volume", "42"), ("future_x", "hello")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.HEALTHY


class TestCorruptDatabase:
    def test_not_a_database(self, tmp_path):
        db = tmp_path / "garbage.db"
        db.write_bytes(b"THIS IS NOT SQLITE")
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.CORRUPT_DATABASE
        # Not deleted, not modified
        assert db.exists()
        assert db.read_bytes() == b"THIS IS NOT SQLITE"


class TestMalformedData:
    def test_volume_not_integer(self, tmp_path):
        db = tmp_path / "badvol.db"
        _write_raw_rows(db, [("volume", "abc")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA

    def test_volume_out_of_range(self, tmp_path):
        db = tmp_path / "volrange.db"
        _write_raw_rows(db, [("volume", "101")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA

    def test_muted_invalid(self, tmp_path):
        db = tmp_path / "badmute.db"
        _write_raw_rows(db, [("muted", "maybe")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA

    def test_recent_files_bad_json(self, tmp_path):
        db = tmp_path / "badjson.db"
        _write_raw_rows(db, [("recent_files", "{broken")])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA

    def test_recent_files_wrong_shape(self, tmp_path):
        db = tmp_path / "badshape.db"
        _write_raw_rows(db, [("recent_files", json.dumps({"a": 1}))])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA

    def test_recent_files_non_string_items(self, tmp_path):
        db = tmp_path / "baditems.db"
        _write_raw_rows(db, [("recent_files", json.dumps(["a.mp3", 12]))])
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health == PersistenceHealth.MALFORMED_DATA


class TestLockedDatabase:
    def test_locked_classified(self, tmp_path):
        db = tmp_path / "locked.db"
        conn1 = sqlite3.connect(str(db))
        conn1.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn1.execute("BEGIN EXCLUSIVE")
        try:
            result = SQLiteSettingsRepository.inspect_path(db)
            assert result.health == PersistenceHealth.LOCKED
        finally:
            conn1.rollback()
            conn1.close()


class TestNoSideEffects:
    def test_corrupt_file_unchanged_after_inspection(self, tmp_path):
        db = tmp_path / "preserve.db"
        db.write_bytes(b"garbage bytes")
        before = db.read_bytes()
        SQLiteSettingsRepository.inspect_path(db)
        assert db.read_bytes() == before

    def test_malformed_rows_unchanged(self, tmp_path):
        db = tmp_path / "keep.db"
        _write_raw_rows(db, [("volume", "abc")])
        before = db.read_bytes()
        SQLiteSettingsRepository.inspect_path(db)
        assert db.read_bytes() == before


class TestUnknownFailureSafety:
    def test_unknown_sqlite_error_is_not_corruption(self):
        exc = sqlite3.OperationalError("some future sqlite failure")
        result = sqlite_settings._classify_sqlite_error(exc)
        assert result.health is PersistenceHealth.UNKNOWN_FAILURE
        assert result.health is not PersistenceHealth.CORRUPT_DATABASE

    def test_known_notadb_is_corruption(self):
        exc = sqlite3.DatabaseError("file is not a database")
        exc.sqlite_errorcode = sqlite_settings._SQLITE_NOTADB
        result = sqlite_settings._classify_sqlite_error(exc)
        assert result.health is PersistenceHealth.CORRUPT_DATABASE

    def test_access_codes_classified(self):
        for code in (
            sqlite_settings._SQLITE_READONLY,
            sqlite_settings._SQLITE_CANTOPEN,
            sqlite_settings._SQLITE_PERM,
        ):
            exc = sqlite3.OperationalError("access denied")
            exc.sqlite_errorcode = code
            result = sqlite_settings._classify_sqlite_error(exc)
            assert result.health is PersistenceHealth.ACCESS_FAILURE

    def test_io_codes_classified(self):
        exc = sqlite3.OperationalError("disk i/o error")
        exc.sqlite_errorcode = sqlite_settings._SQLITE_IOERR
        result = sqlite_settings._classify_sqlite_error(exc)
        assert result.health is PersistenceHealth.IO_FAILURE


class TestSchemaClassification:
    def test_missing_settings_table_is_malformed(self, tmp_path):
        db = tmp_path / "noschema.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE other (x INTEGER)")
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health is PersistenceHealth.MALFORMED_DATA

    def test_wrong_columns_is_malformed(self, tmp_path):
        db = tmp_path / "badcols.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY)")
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health is PersistenceHealth.MALFORMED_DATA

    def test_empty_valid_schema_healthy(self, tmp_path):
        db = tmp_path / "empty.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health is PersistenceHealth.HEALTHY


class TestReadOnlyInspection:
    def test_inspection_uses_read_only_uri(self):
        uri = sqlite_settings._read_only_uri(Path("/tmp/with space/música.db"))
        assert uri.endswith("?mode=ro")
        assert "file:" in uri

    def test_inspection_no_wal_shm_creation(self, tmp_path):
        db = tmp_path / "nourls.db"
        _write_raw_rows(db, [("volume", "42")])
        SQLiteSettingsRepository.inspect_path(db)
        assert not db.with_name(db.name + "-wal").exists()
        assert not db.with_name(db.name + "-shm").exists()
