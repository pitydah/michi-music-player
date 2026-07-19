from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from core.library.library_filtered_query_service import LibraryFilteredQueryService
from core.library.library_query_service import LibraryQueryService

pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def service():
    connection = sqlite3.connect(":memory:")
    connection.execute("""
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            filename TEXT,
            directory TEXT,
            ext TEXT,
            duration REAL,
            title TEXT,
            artist TEXT,
            album TEXT,
            albumartist TEXT,
            year INTEGER,
            genre TEXT,
            composer TEXT,
            track_number INTEGER,
            track_total INTEGER,
            disc_number INTEGER,
            disc_total INTEGER,
            bitrate INTEGER,
            sample_rate INTEGER,
            bit_depth INTEGER,
            channels INTEGER,
            play_count INTEGER,
            last_played REAL,
            album_key TEXT,
            track_uid TEXT,
            created_at REAL,
            quality TEXT,
            scan_status TEXT,
            deleted_at REAL
        )
    """)
    connection.execute("CREATE TABLE favorites (track_id TEXT UNIQUE)")
    rows = [
        (1, "/music/a.flac", "a.flac", "/music", ".flac", 200, "Alpha", "A", "First", "A",
         2020, "Jazz", "Composer One", 1, 2, 1, 1, 900, 96000, 24, 2, 4, 1, "first", "u1", 1,
         "hires", "ok", None),
        (2, "/music/b.mp3", "b.mp3", "/music", ".mp3", 180, "Beta", "B", "Second", "B",
         2021, "Rock", "Composer Two", 1, 1, 1, 1, 320, 44100, 16, 2, 0, None, "second", "u2", 2,
         "standard", "ok", None),
        (3, "/offline/c.flac", "c.flac", "/offline", ".flac", 240, "Gamma", "A", "First", "A",
         2020, "Jazz", "Composer One", 2, 2, 1, 1, 1000, 192000, 24, 2, 0, None, "first", "u3", 3,
         "hires", "missing", None),
    ]
    connection.executemany(
        "INSERT INTO media_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    connection.execute("INSERT INTO favorites(track_id) VALUES (?)", ("/music/a.flac",))
    connection.commit()

    canonical = LibraryQueryService(db=SimpleNamespace(conn=connection))
    filtered = LibraryFilteredQueryService(canonical)
    yield filtered
    connection.close()


def test_filter_contract_count_and_page_are_consistent(service):
    filters = dict(genre="Jazz", composer="Composer One", year="2020", fmt="flac")
    assert service.count_tracks(**filters) == 2
    page = service.fetch_tracks(offset=0, limit=50, **filters)
    assert len(page) == 2
    assert {track["title"] for track in page} == {"Alpha", "Gamma"}


def test_favorites_filter(service):
    assert service.count_tracks(favorites=True) == 1
    assert service.fetch_tracks(favorites=True)[0]["title"] == "Alpha"


def test_unplayed_filter(service):
    assert service.count_tracks(unplayed=True) == 2
    assert {track["title"] for track in service.fetch_tracks(unplayed=True)} == {"Beta", "Gamma"}


def test_missing_filter(service):
    assert service.count_tracks(missing=True) == 1
    missing = service.fetch_tracks(missing=True)
    assert missing[0]["title"] == "Gamma"


def test_sort_and_pagination(service):
    first = service.fetch_tracks(offset=0, limit=1, sort="year", asc=False)
    second = service.fetch_tracks(offset=1, limit=1, sort="year", asc=False)
    assert len(first) == 1
    assert len(second) == 1
    assert first[0]["track_id"] != second[0]["track_id"]


def test_invalid_year_is_safe_and_empty(service):
    assert service.count_tracks(year="not-a-year") == 0
    assert service.fetch_tracks(year="not-a-year") == []
