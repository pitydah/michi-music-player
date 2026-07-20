from __future__ import annotations

import sqlite3

from library.batch_writer import BatchWriter
from library.schema import Schema


def _record(filepath: str, **overrides) -> dict:
    record = {
        "filepath": filepath,
        "filename": filepath.rsplit("/", 1)[-1],
        "directory": filepath.rsplit("/", 1)[0] or "/",
        "ext": ".flac",
        "kind": "audio",
        "size": 100,
        "mtime": 1.0,
        "duration": 180.0,
        "channels": 2,
        "sample_rate": 44100,
        "bitrate": 1000000,
        "title": "Song",
        "artist": "Artist",
        "album": "Album",
        "albumartist": "Album Artist",
        "year": 2024,
        "genre": "Rock",
        "track_number": 1,
        "track_total": 10,
        "disc_number": 1,
        "disc_total": 1,
        "composer": "",
        "mb_track_id": "",
        "mb_album_id": "",
        "mb_albumartist_id": "",
        "bit_depth": 24,
        "bpm": 120,
        "content_hash": "content",
        "track_uid": "uid-1",
        "created_at": 1.0,
        "updated_at": 1.0,
        "last_scanned": 1.0,
        "scan_status": "ok",
    }
    record.update(overrides)
    return record


def test_writer_generates_and_persists_stable_album_key():
    connection = sqlite3.connect(":memory:")
    Schema.initialize(connection)
    writer = BatchWriter(connection)
    writer.add(_record("/music/song.flac"))
    writer.flush()

    row = connection.execute(
        "SELECT album_key, normalized_album, normalized_albumartist, metadata_hash "
        "FROM media_items WHERE filepath=?",
        ("/music/song.flac",),
    ).fetchone()

    assert row[0]
    assert row[1] == "album"
    assert row[2] == "album artist"
    assert len(row[3]) == 64
    connection.close()


def test_metadata_upsert_preserves_user_owned_playback_state():
    connection = sqlite3.connect(":memory:")
    Schema.initialize(connection)
    writer = BatchWriter(connection)
    writer.add(_record(
        "/music/song.flac",
        rating=5,
        play_count=17,
        last_played=1234.0,
    ))
    writer.flush()

    writer.add(_record(
        "/music/song.flac",
        title="Updated title",
        rating=0,
        play_count=0,
        last_played=0.0,
        updated_at=2.0,
    ))
    writer.flush()

    row = connection.execute(
        "SELECT title, rating, play_count, last_played "
        "FROM media_items WHERE filepath=?",
        ("/music/song.flac",),
    ).fetchone()

    assert row == ("Updated title", 5, 17, 1234.0)
    connection.close()


def test_writer_normalizes_numeric_metadata():
    connection = sqlite3.connect(":memory:")
    Schema.initialize(connection)
    writer = BatchWriter(connection)
    writer.add(_record(
        "/music/invalid.flac",
        year="9999",
        track_number=4,
        track_total=12,
        disc_number=2,
        disc_total=3,
        bpm="120.4",
    ))
    writer.flush()

    row = connection.execute(
        "SELECT year, track_number, track_total, disc_number, disc_total, bpm "
        "FROM media_items WHERE filepath=?",
        ("/music/invalid.flac",),
    ).fetchone()

    assert row == (0, 4, 12, 2, 3, 120)
    connection.close()
