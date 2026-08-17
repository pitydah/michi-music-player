"""M5.C1 schema versioning + migration 0->1 — RED/GREEN tests.

The settings key/value table carries the schema version row
(`schema_version = "1"`). Version interpretation:
- row absent or non-integer value -> version 0 (malformed -> WARNING and
  treated as v0; the canonical "1" overwrites it during migration);
- integer value > CURRENT_SCHEMA_VERSION -> fail closed with a typed
  SchemaVersionError (never downgrade, never rewrite);
- migration runs ONLY on the writable open path (the repository
  constructor / _ensure_schema flow), never in the read-only preflight.
"""

import json
import logging
import sqlite3
from pathlib import Path

import pytest

from michi.domain.persistence_health import PersistenceHealth
from michi.infrastructure import sqlite_settings as sqlite_settings_mod
from michi.infrastructure.sqlite_settings import (
    CURRENT_SCHEMA_VERSION,
    SchemaVersionError,
    SQLiteSettingsRepository,
)

_LOGGER_NAME = "michi.infrastructure.sqlite_settings"

_V0_ROWS = [
    ("volume", "37"),
    ("muted", "true"),
    ("last_directory", "/music"),
    ("recent_files", json.dumps(["a.mp3", "b.mp3"])),
]


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_rows(db_path):
    """Read settings rows read-only without mutating the database."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return conn.execute("SELECT key, value FROM settings").fetchall()


def _read_raw_settings(db_path):
    return dict(_read_raw_rows(db_path))


def _remove_wal_sidecars(db_path):
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def test_v0_migrates_to_v1_preserving_settings(tmp_path):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, _V0_ROWS)
    assert "schema_version" not in _read_raw_settings(db)

    SQLiteSettingsRepository(db)

    rows = _read_raw_settings(db)
    assert rows["schema_version"] == "1"
    assert rows["volume"] == "37"
    assert rows["muted"] == "true"
    assert rows["last_directory"] == "/music"
    assert rows["recent_files"] == json.dumps(["a.mp3", "b.mp3"])


def test_v1_open_is_noop(tmp_path):
    db = tmp_path / "michi.db"
    rows = [("schema_version", "1")] + _V0_ROWS
    _write_raw_rows(db, rows)
    before = _read_raw_rows(db)

    SQLiteSettingsRepository(db)
    after_first = _read_raw_rows(db)
    assert after_first == before

    SQLiteSettingsRepository(db)
    assert _read_raw_rows(db) == before


def test_migration_failure_rolls_back(tmp_path, monkeypatch):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, _V0_ROWS)

    def _exploding_migrate(conn):
        conn.execute("BEGIN")
        conn.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES('schema_version', '1')"
        )
        raise RuntimeError("forced migration failure after writing the version row")

    monkeypatch.setattr(sqlite_settings_mod, "_migrate_0_to_1", _exploding_migrate)

    with pytest.raises(RuntimeError, match="forced migration failure"):
        SQLiteSettingsRepository(db)

    # Fresh connection: the transaction was rolled back — still v0.
    rows = _read_raw_settings(db)
    assert "schema_version" not in rows
    assert rows["volume"] == "37"
    assert rows["muted"] == "true"
    assert rows["last_directory"] == "/music"
    assert rows["recent_files"] == json.dumps(["a.mp3", "b.mp3"])


def test_future_version_fails_closed(tmp_path):
    db = tmp_path / "michi.db"
    rows = [("schema_version", "99"), ("volume", "42"), ("muted", "false")]
    _write_raw_rows(db, rows)

    with pytest.raises(SchemaVersionError) as exc_info:
        SQLiteSettingsRepository(db)

    assert "99" in str(exc_info.value)
    assert "newer" in str(exc_info.value)
    # Fail closed: the database was NOT rewritten.
    after = _read_raw_settings(db)
    assert after["schema_version"] == "99"
    assert after["volume"] == "42"
    assert after["muted"] == "false"


def test_malformed_schema_version_falls_back(tmp_path, caplog):
    db = tmp_path / "michi.db"
    _write_raw_rows(
        db, [("schema_version", "abc"), ("volume", "37"), ("muted", "true")]
    )

    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        SQLiteSettingsRepository(db)

    rows = _read_raw_settings(db)
    assert rows["schema_version"] == "1"
    assert rows["volume"] == "37"
    assert rows["muted"] == "true"
    assert any("Malformed schema_version" in r.message for r in caplog.records)


def test_fresh_install_has_schema_version(tmp_path):
    db = tmp_path / "michi.db"
    repo = SQLiteSettingsRepository(db)

    assert _read_raw_settings(db)["schema_version"] == "1"
    state = repo.load()
    assert state.volume == 80
    assert state.muted is False
    assert state.last_directory == ""
    assert state.recent_files == []


def test_lkg_v0_recovery_migrates(tmp_path):
    db = tmp_path / "michi.db"
    # Healthy v0 primary (raw rows, no schema_version row).
    _write_raw_rows(db, _V0_ROWS)
    assert (
        SQLiteSettingsRepository.refresh_last_known_good(db).health
        is PersistenceHealth.HEALTHY
    )
    lkg = SQLiteSettingsRepository.last_known_good_path(db)
    assert "schema_version" not in _read_raw_settings(lkg)

    # Corrupt the primary after removing its sidecars.
    _remove_wal_sidecars(db)
    db.write_bytes(b"THIS IS NOT SQLITE")

    repo = SQLiteSettingsRepository.open_for_startup(db)

    assert isinstance(repo, SQLiteSettingsRepository)
    # The v0 LKG copy was installed, then the writable open migrated it.
    rows = _read_raw_settings(db)
    assert rows["schema_version"] == "1"
    assert rows["volume"] == "37"
    assert rows["muted"] == "true"
    assert rows["last_directory"] == "/music"
    assert rows["recent_files"] == json.dumps(["a.mp3", "b.mp3"])

    # A fresh repository reads the same migrated values.
    fresh = SQLiteSettingsRepository(db)
    assert fresh.load().volume == 37
    assert fresh.load().muted is True
    assert fresh.load().last_directory == "/music"
    assert fresh.load().recent_files == ["a.mp3", "b.mp3"]


def test_readonly_preflight_does_not_migrate(tmp_path):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, [("volume", "42"), ("muted", "true")])

    diag = SQLiteSettingsRepository.inspect_path(db)
    assert diag.health is PersistenceHealth.HEALTHY
    # Read-only inspection alone never writes the version row.
    assert "schema_version" not in _read_raw_settings(db)

    # The writable open performs the migration.
    SQLiteSettingsRepository(db)
    rows = _read_raw_settings(db)
    assert rows["schema_version"] == "1"
    assert rows["volume"] == "42"
    assert rows["muted"] == "true"


def test_defaults_preserved_on_migrated_db(tmp_path):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, _V0_ROWS)

    repo = SQLiteSettingsRepository(db)
    state = repo.load()

    assert state.volume == 37
    assert state.muted is True
    assert state.last_directory == "/music"
    assert state.recent_files == ["a.mp3", "b.mp3"]
    assert CURRENT_SCHEMA_VERSION == 1
    assert _read_raw_settings(db)["schema_version"] == "1"
