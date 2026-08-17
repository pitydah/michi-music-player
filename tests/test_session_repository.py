"""M5.C2 SQLite session snapshot repository — RED/GREEN tests.

The repository persists one session snapshot into the shared settings
key/value table under the key "session_snapshot". load() never raises
and never overwrites malformed persisted data (safe read fallback);
save() is best effort. Rows written by other components coexist untouched.
"""

import sqlite3

from michi.domain.queue import RepeatMode
from michi.domain.session import (
    PersistedQueueEntry,
    PlaybackSessionSnapshot,
    encode_snapshot,
    fresh_snapshot,
)
from michi.infrastructure.session_repository import SqliteSessionRepository

_SESSION_KEY = "session_snapshot"


def _full_snapshot() -> PlaybackSessionSnapshot:
    return PlaybackSessionSnapshot(
        format_version=1,
        queue_entries=(
            PersistedQueueEntry(file_path="X1", title="Alpha"),
            PersistedQueueEntry(file_path="X2", title="Beta"),
            PersistedQueueEntry(file_path="X1", title="Gamma"),
        ),
        queue_current_index=2,
        playback_path="X2",
        position_ms=222000,
        repeat_mode=RepeatMode.ALL,
        shuffle_enabled=True,
        shuffle_seed=424242,
    )


def _read_rows(db_path):
    """Raw settings rows read-only, without mutating the database."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def test_round_trip(tmp_path):
    db = tmp_path / "michi.db"
    snapshot = _full_snapshot()
    SqliteSessionRepository(db).save(snapshot)

    loaded = SqliteSessionRepository(db).load()
    assert loaded == snapshot

    rows = dict(_read_rows(db))
    assert rows[_SESSION_KEY] == encode_snapshot(snapshot)


def test_fresh_db_load_empty(tmp_path):
    db = tmp_path / "michi.db"
    assert SqliteSessionRepository(db).load() == fresh_snapshot()


def test_missing_row_load_empty(tmp_path):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, [("volume", "42"), ("muted", "true")])
    assert SqliteSessionRepository(db).load() == fresh_snapshot()


def test_malformed_row_loads_fresh_without_overwrite(tmp_path):
    db = tmp_path / "michi.db"
    garbage = "this is not a session snapshot"
    _write_raw_rows(db, [(_SESSION_KEY, garbage)])
    repo = SqliteSessionRepository(db)

    assert repo.load() == fresh_snapshot()
    # Safe read fallback never overwrites the malformed original (M11.2C).
    assert dict(_read_rows(db))[_SESSION_KEY] == garbage


def test_settings_rows_coexist(tmp_path):
    db = tmp_path / "michi.db"
    _write_raw_rows(db, [("volume", "42"), ("muted", "true")])
    SqliteSessionRepository(db).save(_full_snapshot())

    rows = dict(_read_rows(db))
    assert rows["volume"] == "42"
    assert rows["muted"] == "true"
    assert rows[_SESSION_KEY] == encode_snapshot(_full_snapshot())


def test_load_never_raises(tmp_path, monkeypatch):
    """load() degrades to a fresh snapshot on sqlite errors.

    Deterministic approach: monkeypatch sqlite3.connect to raise
    sqlite3.Error instead of corrupting the DB file. A corrupt file
    (e.g. b"THIS IS NOT SQLITE") would also make the constructor's
    schema ensure raise, so the file approach cannot exercise a repo
    instance cleanly; the monkeypatch exercises the exact error path
    load() must survive.
    """
    db = tmp_path / "michi.db"
    repo = SqliteSessionRepository(db)

    def _exploding_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(sqlite3, "connect", _exploding_connect)
    assert repo.load() == fresh_snapshot()
