from __future__ import annotations

import sqlite3

import pytest

from core.mix_query_service import MixQueryError, MixQueryService


class _Factory:
    def __init__(self, connection):
        self._connection = connection

    def get_connection(self):
        return self._connection


def _service() -> MixQueryService:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            albumartist TEXT,
            album_key TEXT,
            duration REAL,
            ext TEXT,
            year INTEGER,
            genre TEXT,
            bitrate INTEGER,
            sample_rate INTEGER,
            bit_depth INTEGER,
            channels INTEGER,
            track_uid TEXT,
            play_count INTEGER,
            last_played INTEGER,
            created_at INTEGER,
            date_added INTEGER,
            track_number INTEGER,
            disc_number INTEGER,
            deleted_at INTEGER
        );
        CREATE TABLE favorites (track_id TEXT, added_at INTEGER);
        """
    )
    rows = [
        (
            1,
            "/music/a.flac",
            "A",
            "Artist 1",
            "Album 1",
            "",
            "album-1",
            180,
            "flac",
            1994,
            "Rock",
            1000,
            96000,
            24,
            2,
            "uid-1",
            5,
            10,
            1,
            1,
            1,
            1,
            None,
        ),
        (
            2,
            "/music/b.mp3",
            "B",
            "Artist 1",
            "Album 1",
            "",
            "album-1",
            200,
            "mp3",
            1995,
            "Rock",
            320,
            44100,
            16,
            2,
            "uid-2",
            0,
            0,
            2,
            2,
            2,
            1,
            None,
        ),
        (
            3,
            "/music/c.mp3",
            "C",
            "Artist 2",
            "Album 2",
            "",
            "album-2",
            220,
            "mp3",
            2001,
            "Jazz",
            192,
            44100,
            16,
            2,
            "uid-3",
            2,
            1,
            3,
            3,
            1,
            1,
            None,
        ),
    ]
    connection.executemany(
        "INSERT INTO media_items VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    connection.execute(
        "INSERT INTO favorites VALUES (?, ?)",
        ("uid-1", 100),
    )
    connection.commit()
    return MixQueryService(connection_factory=_Factory(connection))


def test_category_queries_are_queue_ready():
    service = _service()
    favorite = service.favorites(limit=10)[0]
    assert favorite["track_id"] == 1
    assert favorite["filepath"] == "/music/a.flac"
    assert favorite["format"] == "flac"
    assert service.unplayed(limit=10)[0]["track_id"] == 2
    assert [
        track["track_id"]
        for track in service.by_album("Album 1", limit=10)
    ] == [1, 2]


def test_parameterized_queries_do_not_misbind_limit():
    service = _service()
    assert len(service.by_field("artist", "Artist 1", limit=1)) == 1
    assert {
        track["track_id"]
        for track in service.by_decade(1990, limit=10)
    } == {1, 2}
    assert [
        track["track_id"]
        for track in service.by_year(2001, limit=10)
    ] == [3]
    assert {
        track["track_id"]
        for track in service.high_quality(320, limit=10)
    } == {1, 2}


def test_custom_filters_match_generator_contract():
    service = _service()
    tracks = service.custom(
        {
            "seed_artist": "Artist 1",
            "year_from": 1990,
            "year_to": 1999,
            "quality": "lossless",
        },
        limit=25,
    )
    assert [track["track_id"] for track in tracks] == [1]


def test_arbitrary_mutation_sql_is_rejected():
    service = _service()
    with pytest.raises(MixQueryError) as error:
        service.fetch_tracks("DELETE FROM media_items", [], 10)
    assert error.value.code == "UNSAFE_QUERY"
