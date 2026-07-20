from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from core.library.library_filtered_query_service import LibraryFilteredQueryService
from core.library.library_query_service import LibraryQueryService
from library.batch_writer import BatchWriter
from library.schema import Schema

pytestmark = [pytest.mark.qml_module("library")]


def _record(track_id: int, filepath: str, **overrides) -> dict:
    title = overrides.pop("title", f"Track {track_id}")
    record = {
        "filepath": filepath,
        "filename": filepath.rsplit("/", 1)[-1],
        "directory": filepath.rsplit("/", 1)[0],
        "ext": ".flac",
        "kind": "audio",
        "size": 1000,
        "mtime": float(track_id),
        "duration": 200.0,
        "channels": 2,
        "sample_rate": 96000,
        "bitrate": 900000,
        "title": title,
        "artist": "A",
        "album": "First",
        "albumartist": "A",
        "year": 2020,
        "genre": "Jazz",
        "track_number": track_id,
        "track_total": 2,
        "disc_number": 1,
        "disc_total": 1,
        "composer": "Composer One",
        "mb_track_id": "",
        "mb_album_id": "",
        "mb_albumartist_id": "",
        "bit_depth": 24,
        "bpm": 120,
        "replaygain_track": 0.0,
        "replaygain_album": 0.0,
        "replaygain_track_peak": 0.0,
        "isrc": "",
        "label": "",
        "conductor": "",
        "compilation": 0,
        "media_type": "",
        "encoder": "",
        "copyright": "",
        "originaldate": "",
        "remixer": "",
        "grouping": "",
        "mood": "",
        "comment": "",
        "lyricist": "",
        "replaygain_album_peak": 0.0,
        "r128_track_gain": 0.0,
        "r128_album_gain": 0.0,
        "mb_artist_id": "",
        "mb_releasegroup_id": "",
        "acoustid_id": "",
        "acoustid_fingerprint": "",
        "content_hash": f"content-{track_id}",
        "track_uid": f"uid-{track_id}",
        "created_at": float(track_id),
        "updated_at": float(track_id),
        "last_scanned": float(track_id),
        "scan_status": "ok",
    }
    record.update(overrides)
    return record


@pytest.fixture
def service():
    connection = sqlite3.connect(":memory:")
    Schema.initialize(connection)
    writer = BatchWriter(connection)
    writer.add(_record(
        1,
        "/music/Jazz/a.flac",
        title="Álpha",
        play_count=4,
        last_played=10.0,
        album_key="first",
    ))
    writer.add(_record(
        2,
        "/music/Rock/b.mp3",
        title="Beta",
        artist="B",
        album="Second",
        albumartist="B",
        year=2021,
        genre="Rock",
        composer="Composer Two",
        ext=".mp3",
        sample_rate=44100,
        bitrate=320000,
        bit_depth=16,
        track_number=1,
        track_total=1,
        play_count=0,
        album_key="second",
        track_uid="uid-2",
    ))
    writer.add(_record(
        3,
        "/offline/Jazz/c.flac",
        title="Gamma",
        track_number=2,
        play_count=0,
        scan_status="missing",
        album_key="first",
        track_uid="uid-3",
    ))
    writer.flush()
    connection.execute(
        "INSERT INTO favorites(track_id) VALUES (?)",
        ("uid-1",),
    )
    connection.execute(
        "INSERT INTO play_history(track_id, played_at) VALUES (?, ?)",
        ("uid-1", 100.0),
    )
    connection.commit()

    canonical = LibraryQueryService(db=SimpleNamespace(conn=connection))
    filtered = LibraryFilteredQueryService(canonical)
    yield filtered
    connection.close()


def test_filter_contract_count_and_page_are_consistent(service):
    filters = dict(
        genre="Jazz",
        composer="Composer One",
        year="2020",
        fmt="flac",
    )
    assert service.count_tracks(**filters) == 2
    page = service.fetch_tracks(offset=0, limit=50, **filters)
    assert len(page) == 2
    assert {track["title"] for track in page} == {"Álpha", "Gamma"}


def test_accent_insensitive_search_uses_normalized_columns(service):
    page = service.fetch_tracks(search="alpha")
    assert [track["title"] for track in page] == ["Álpha"]


def test_favorites_match_track_uid(service):
    assert service.count_tracks(favorites=True) == 1
    favorite = service.fetch_tracks(favorites=True)[0]
    assert favorite["title"] == "Álpha"
    assert favorite["favorite"] is True


def test_unplayed_and_missing_filters(service):
    assert {track["title"] for track in service.fetch_tracks(unplayed=True)} == {
        "Beta",
        "Gamma",
    }
    missing = service.fetch_tracks(missing=True)
    assert [track["title"] for track in missing] == ["Gamma"]
    assert missing[0]["missing"] is True


def test_track_rows_expose_metadata_health(service):
    track = service.fetch_tracks(sort="metadata", asc=False)[0]
    assert track["composer"]
    assert track["metadata_completeness"] > 0
    assert 0.0 <= track["metadata_confidence"] <= 1.0
    assert len(track["metadata_hash"]) == 64


def test_album_and_artist_models_share_active_filters(service):
    assert service.count_albums(genre="Jazz", composer="Composer One") == 1
    albums = service.fetch_albums(genre="Jazz", composer="Composer One")
    assert albums[0]["title"] == "First"
    assert albums[0]["track_count"] == 2
    assert albums[0]["disc_count"] == 1
    assert "FLAC" in albums[0]["formats"]
    assert albums[0]["metadata_completeness"] > 0

    assert service.count_artists(fmt="mp3") == 1
    artists = service.fetch_artists(fmt="mp3")
    assert artists[0]["name"] == "B"
    assert artists[0]["metadata_completeness"] > 0


def test_detail_queries_return_real_metadata(service):
    album_tracks = service.fetch_album_tracks_internal("first")
    artist_tracks = service.fetch_artist_tracks_internal("A")

    assert [track["track_number"] for track in album_tracks] == [1, 2]
    assert album_tracks[0]["album"] == "First"
    assert artist_tracks[0]["artist"] == "A"
    assert artist_tracks[0]["year"] == 2020


def test_folder_filter_respects_path_boundary(service):
    assert service.count_tracks(folder="/music/Jazz") == 1
    assert service.count_tracks(folder="/music/Ja") == 0


def test_sort_and_pagination_are_deterministic(service):
    first = service.fetch_tracks(offset=0, limit=1, sort="year", asc=False)
    second = service.fetch_tracks(offset=1, limit=1, sort="year", asc=False)
    assert len(first) == 1
    assert len(second) == 1
    assert first[0]["track_id"] != second[0]["track_id"]


def test_invalid_year_is_safe_and_empty(service):
    assert service.count_tracks(year="not-a-year") == 0
    assert service.fetch_tracks(year="not-a-year") == []


def test_recently_played_uses_real_catalogue_schema(service):
    recent = service.recently_played()
    assert len(recent) == 1
    assert recent[0]["title"] == "Álpha"
    assert recent[0]["played_at"] == 100.0


def test_catalogue_metadata_summary(service):
    summary = service.catalogue_metadata_summary()
    assert summary["track_count"] == 3
    assert summary["average_completeness"] > 0
    assert summary["unhashed_count"] == 0
