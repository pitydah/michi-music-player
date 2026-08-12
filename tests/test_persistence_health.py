"""M11.2A persistence health detection tests — real SQLite + temp files."""

import json
import sqlite3

from michi.domain.persistence_health import PersistenceHealth
from michi.domain.settings import SettingsState
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
