"""M6.2 persistent library index — RED/GREEN tests.

The index persists one row per track (track_id, file_size, mtime_ns, full
TrackMetadata JSON) in a bounded sqlite context owned exclusively by the
library index (tables ``library_index`` + ``library_meta`` — the settings/
session/prefs tables are never touched and the M5 ``schema_version`` key
space is not reused). The codec is strict and deterministic: any malformed
row is logged and skipped on load (never a crash, never fabricated partial
metadata); the schema version fails closed when the database is newer than
this build supports; upsert_many is an all-or-nothing transaction.
"""

import json
import logging
import sqlite3
from dataclasses import asdict

import pytest

from michi.application.ports import LibraryIndexRepository
from michi.domain.library import (
    TrackMetadata,
    make_album_key,
    make_composer_key,
    make_track_id,
)
from michi.domain.library_index import (
    LibraryIndexEntry,
    decode_index_metadata,
    encode_index_metadata,
)
from michi.infrastructure.library_index import (
    LibraryIndexSchemaError,
    SqliteLibraryIndexRepository,
)


def _full_metadata() -> TrackMetadata:
    """All 25 TrackMetadata fields set to non-default values."""
    return TrackMetadata(
        title="Born to Run",
        artist="Bruce Springsteen",
        album="Born to Run",
        duration_ms=269000,
        genre="Rock",
        year=1975,
        album_artist="Bruce Springsteen",
        track_number=1,
        track_total=8,
        disc_number=1,
        disc_total=1,
        composer="Bruce Springsteen",
        date="1975-08-25",
        compilation=False,
        sort_title="Born to Run",
        sort_artist="Springsteen, Bruce",
        sort_album="Born to Run",
        sort_album_artist="Springsteen, Bruce",
        codec="mp3",
        container="mp3",
        sample_rate_hz=44100,
        bit_depth=16,
        channels=2,
        bitrate_bps=320000,
        file_size=12345678,
    )


def _make_entry(
    track_id: str,
    *,
    file_size: int = 12345678,
    mtime_ns: int = 1_600_000_000_000_000_000,
    metadata: TrackMetadata | None = None,
) -> LibraryIndexEntry:
    return LibraryIndexEntry(
        track_id=track_id,
        file_size=file_size,
        mtime_ns=mtime_ns,
        metadata=metadata if metadata is not None else _full_metadata(),
    )


def _table_names(db_path) -> set[str]:
    with sqlite3.connect(str(db_path)) as conn:
        return {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def test_fresh_db_empty_and_version(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    assert issubclass(SqliteLibraryIndexRepository, LibraryIndexRepository)

    assert repo.load_all() == ()
    assert repo.version() == 1

    # The bounded-context tables exist with the exact contract columns.
    assert {"library_index", "library_meta"} <= _table_names(db)
    with sqlite3.connect(str(db)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(library_index)")}
    assert cols == {"track_id", "file_size", "mtime_ns", "metadata"}
    with sqlite3.connect(str(db)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(library_meta)")}
    assert cols == {"key", "value"}


def test_write_read_roundtrip(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    entry = _make_entry(make_track_id(tmp_path / "alpha.mp3"))

    repo.upsert_many((entry,))

    assert repo.load_all() == (entry,)


def test_restart_reload(tmp_path):
    db = tmp_path / "michi.db"
    entry = _make_entry(make_track_id(tmp_path / "alpha.mp3"))
    SqliteLibraryIndexRepository(db).upsert_many((entry,))

    # A brand-new repository on the SAME database survives reconstruction.
    assert SqliteLibraryIndexRepository(db).load_all() == (entry,)


def test_missing_row_absent(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    present = make_track_id(tmp_path / "present.mp3")
    absent = make_track_id(tmp_path / "absent.mp3")
    repo.upsert_many((_make_entry(present),))

    loaded = repo.load_all()
    assert present in [e.track_id for e in loaded]
    assert absent not in [e.track_id for e in loaded]
    # load never crashes for any track id (nothing to look up by id).
    assert repo.load_all() == loaded


def test_malformed_metadata_row_skipped(tmp_path, caplog):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    valid = _make_entry(make_track_id(tmp_path / "valid.mp3"))
    repo.upsert_many((valid,))

    # Fabricate a row with garbage metadata JSON using raw sqlite3.
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "INSERT INTO library_index(track_id, file_size, mtime_ns, metadata) "
            "VALUES (?, ?, ?, ?)",
            (make_track_id(tmp_path / "garbage.mp3"), 1, 1, "this is not json"),
        )

    caplog.set_level(logging.WARNING, logger="michi.infrastructure.library_index")
    loaded = repo.load_all()

    # The malformed row is skipped (absent) and the valid row still loads.
    assert loaded == (valid,)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_schema_migration_fresh_to_1(tmp_path):
    db = tmp_path / "michi.db"
    # Fresh database -> tables created and version seeded to 1.
    assert SqliteLibraryIndexRepository(db).version() == 1
    # Reopen -> idempotent no-op, still version 1.
    assert SqliteLibraryIndexRepository(db).version() == 1


def test_future_schema_fails_closed(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    entry = _make_entry(make_track_id(tmp_path / "alpha.mp3"))
    repo.upsert_many((entry,))

    # Simulate a database written by a FUTURE build.
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "UPDATE library_meta SET value = '99' WHERE key = 'library_schema_version'"
        )

    with pytest.raises(LibraryIndexSchemaError):
        SqliteLibraryIndexRepository(db)

    # Fail closed: nothing was rewritten — the version row and the index
    # rows are intact (verified via raw sqlite3).
    with sqlite3.connect(str(db)) as conn:
        assert (
            conn.execute(
                "SELECT value FROM library_meta WHERE key = 'library_schema_version'"
            ).fetchone()[0]
            == "99"
        )
        assert conn.execute("SELECT COUNT(*) FROM library_index").fetchone()[0] == 1


def test_upsert_many_atomic_rollback(tmp_path, monkeypatch):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    entry_a = _make_entry(make_track_id(tmp_path / "a.mp3"))
    entry_b = _make_entry(make_track_id(tmp_path / "b.mp3"))

    # Deterministic injection: a BEFORE INSERT trigger that fires once the
    # table already holds a row (i.e. on the SECOND insert of the batch)
    # and aborts that statement with RAISE(ABORT). RAISE(ABORT) rolls back
    # only the offending statement, leaving the repository's transaction
    # open — so the repo (or its close) rolls the whole batch back. This
    # works regardless of whether the repository executes rows one-by-one
    # or via executemany, and needs no monkeypatching of connection
    # internals: it is the cleanest way to force a mid-batch failure.
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "CREATE TRIGGER boom BEFORE INSERT ON library_index "
            "WHEN (SELECT COUNT(*) FROM library_index) >= 1 "
            "BEGIN SELECT RAISE(ABORT, 'simulated disk I/O error'); END"
        )

    # Best effort: the repository logs the sqlite error, never raises.
    repo.upsert_many((entry_a, entry_b))

    # All-or-nothing: a FRESH connection sees no committed rows.
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute("SELECT COUNT(*) FROM library_index").fetchone()[0] == 0
    finally:
        conn.close()


def test_same_path_updated(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    track_id = make_track_id(tmp_path / "alpha.mp3")
    meta_a = TrackMetadata(title="First", artist="Artist A")
    meta_b = TrackMetadata(title="Second", artist="Artist B")

    repo.upsert_many((_make_entry(track_id, metadata=meta_a),))
    repo.upsert_many((_make_entry(track_id, metadata=meta_b),))

    loaded = repo.load_all()
    assert len(loaded) == 1
    assert loaded[0].track_id == track_id
    assert loaded[0].metadata == meta_b


def test_remove(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    a = make_track_id(tmp_path / "a.mp3")
    b = make_track_id(tmp_path / "b.mp3")
    repo.upsert_many((_make_entry(a), _make_entry(b)))

    repo.remove(a)
    assert [e.track_id for e in repo.load_all()] == [b]

    # Removing an unknown id is a no-op.
    repo.remove(make_track_id(tmp_path / "never-added.mp3"))
    assert [e.track_id for e in repo.load_all()] == [b]


def test_unchanged_entry_reuse_idempotent(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    entry = _make_entry(make_track_id(tmp_path / "alpha.mp3"))

    repo.upsert_many((entry,))
    repo.upsert_many((entry,))

    assert repo.load_all() == (entry,)
    with sqlite3.connect(str(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM library_index").fetchone()[0] == 1


def test_technical_metadata_roundtrip(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    meta = TrackMetadata(
        title="Stems",
        artist="Art",
        codec="flac",
        container="flac",
        sample_rate_hz=96000,
        bit_depth=24,
        channels=2,
        bitrate_bps=0,  # lossless: honest UNKNOWN bitrate, never fabricated
        file_size=987654321,
        duration_ms=412000,
    )
    entry = _make_entry(make_track_id(tmp_path / "stems.flac"), metadata=meta)

    repo.upsert_many((entry,))

    assert repo.load_all() == (entry,)


def test_canonical_identity_inputs_roundtrip(tmp_path):
    db = tmp_path / "michi.db"
    repo = SqliteLibraryIndexRepository(db)
    meta = TrackMetadata(
        album="  Born   to Run  ",
        album_artist="  BRUCE  SPRINGSTEEN ",
        composer="  Bob  Dylan  ",
        genre="Rock",
        year=1975,
        disc_number=1,
        track_number=1,
        title="Thunder Road",
        artist="Bruce Springsteen",
    )
    entry = _make_entry(make_track_id(tmp_path / "alpha.mp3"), metadata=meta)
    repo.upsert_many((entry,))

    reloaded = repo.load_all()[0].metadata
    # The index preserves the canonical identity inputs exactly, so the
    # model-derivation keys recompute identically after a reload.
    assert make_album_key(meta.album, meta.album_artist) == make_album_key(
        reloaded.album, reloaded.album_artist
    )
    assert make_composer_key(meta.composer) == make_composer_key(reloaded.composer)
    assert reloaded.album == meta.album
    assert reloaded.album_artist == meta.album_artist
    assert reloaded.composer == meta.composer


def test_codec_strict_decode():
    meta = _full_metadata()

    # Valid roundtrip == the original TrackMetadata.
    assert decode_index_metadata(encode_index_metadata(meta)) == meta

    # Not JSON -> None.
    assert decode_index_metadata("not json") is None
    # List payload -> None (must be a JSON object).
    assert decode_index_metadata("[1, 2]") is None
    # Scalar payload -> None.
    assert decode_index_metadata('"just a string"') is None
    # Empty object -> missing fields -> None.
    assert decode_index_metadata("{}") is None

    # Missing field -> None.
    missing = asdict(meta)
    del missing["title"]
    assert decode_index_metadata(json.dumps(missing)) is None

    # Wrong type (track_number as str) -> None.
    wrong_type = asdict(meta)
    wrong_type["track_number"] = "3"
    assert decode_index_metadata(json.dumps(wrong_type)) is None

    # bool-as-int (track_number true) -> None.
    bool_as_int = asdict(meta)
    bool_as_int["track_number"] = True
    assert decode_index_metadata(json.dumps(bool_as_int)) is None

    # bool field must be bool (compilation 1) -> None.
    bool_field_as_int = asdict(meta)
    bool_field_as_int["compilation"] = 1
    assert decode_index_metadata(json.dumps(bool_field_as_int)) is None

    # Extra unknown key is tolerated (future-proof), still decodes.
    extra = asdict(meta)
    extra["future_field"] = "x"
    assert decode_index_metadata(json.dumps(extra)) == meta


@pytest.mark.parametrize("field", list(asdict(_full_metadata()).keys()))
def test_codec_rejects_wrong_type_for_every_field(field):
    payload = asdict(_full_metadata())
    value = payload[field]
    if isinstance(value, str):
        payload[field] = 42  # str fields must be str
    elif isinstance(value, bool):
        payload[field] = "not-a-bool"  # bool fields must be bool
    else:
        payload[field] = True  # int fields must be int-non-bool
    assert decode_index_metadata(json.dumps(payload)) is None


@pytest.mark.parametrize("field", list(asdict(_full_metadata()).keys()))
def test_codec_missing_any_field_rejected(field):
    payload = asdict(_full_metadata())
    del payload[field]
    assert decode_index_metadata(json.dumps(payload)) is None
