from __future__ import annotations
"""Tests for LibraryTrackTable and TrackListModel — 15+ tests."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from ui_qml.models.TrackListModel import TrackListModel
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_tracks.return_value = 10
    qs.fetch_tracks.return_value = [
        {"track_id": 1, "track_uid": "uid1", "title": "Song A",
         "artist": "Artist X", "album": "Album 1", "album_key": "ak1",
         "duration": 200, "format": "FLAC", "year": 2020, "genre": "Rock",
         "track_number": 1, "cover_key": "ck1"},
        {"track_id": 2, "track_uid": "uid2", "title": "Song B",
         "artist": "Artist Y", "album": "Album 2", "album_key": "ak2",
         "duration": 180, "format": "MP3", "year": 2021, "genre": "Pop",
         "track_number": 2, "cover_key": "ck2"},
    ]
    return qs


def test_initial_state(qs):
    m = TrackListModel(query_service=qs)
    assert m.count == 0
    assert not m.loading
    assert not m.initialized


def test_refresh_loads(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    assert m.count == 2
    assert m.totalCount == 10


def test_role_names(qs):
    m = TrackListModel(query_service=qs)
    roles = m.roleNames()
    for expected in [b"trackId", b"trackUid", b"title", b"artist",
                     b"album", b"albumKey", b"duration", b"format",
                     b"year", b"genre", b"trackNumber", b"coverKey"]:
        assert expected in roles.values()


def test_data_access(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, m.TrackIdRole) == 1
    assert m.data(idx, m.TrackUidRole) == "uid1"
    assert m.data(idx, m.TitleRole) == "Song A"
    assert m.data(idx, m.ArtistRole) == "Artist X"
    assert m.data(idx, m.AlbumRole) == "Album 1"
    assert m.data(idx, m.AlbumKeyRole) == "ak1"
    assert m.data(idx, m.DurationRole) == 200
    assert m.data(idx, m.FormatRole) == "FLAC"
    assert m.data(idx, m.YearRole) == 2020
    assert m.data(idx, m.GenreRole) == "Rock"
    assert m.data(idx, m.TrackNumberRole) == 1
    assert m.data(idx, m.CoverKeyRole) == "ck1"


def test_second_track(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    idx = m.index(1, 0)
    assert m.data(idx, m.TitleRole) == "Song B"
    assert m.data(idx, m.FormatRole) == "MP3"
    assert m.data(idx, m.YearRole) == 2021


def test_display_role(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, Qt.DisplayRole) == "Song A"


def test_invalid_index(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    assert m.data(m.index(999, 0)) is None


def test_has_more(qs):
    m = TrackListModel(query_service=qs, page_size=1)
    qs.count_tracks.return_value = 5
    qs.fetch_tracks.return_value = [{"track_id": 1, "title": "A"}]
    m.refresh()
    assert m.hasMore


def test_fetch_more(qs):
    qe = MagicMock()
    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        items = task()
        on_success(items)
        return 1
    qe.submit.side_effect = submit_side
    m = TrackListModel(query_service=qs, page_size=1, query_executor=qe)
    qs.count_tracks.return_value = 3
    qs.fetch_tracks.side_effect = [
        [{"track_id": 1, "title": "A"}],
        [{"track_id": 2, "title": "B"}],
    ]
    m.refresh()
    assert m.count == 1
    assert m.canFetchMore()
    m.fetchMore()
    assert m.count == 2


def test_sort_toggle(qs):
    m = TrackListModel(query_service=qs)
    m.refresh(sort="artist", asc=True)
    assert m._sort == "artist"
    assert m._asc is True


def test_search_filter(qs):
    m = TrackListModel(query_service=qs)
    m.refresh(search="test")
    assert m._search == "test"


def test_format_filter(qs):
    m = TrackListModel(query_service=qs)
    m.refresh(fmt="flac")
    assert m._fmt_filter == "flac"


def test_artist_filter(qs):
    m = TrackListModel(query_service=qs)
    m.refresh(artist="X")
    assert m._artist_filter == "X"


def test_reset(qs):
    m = TrackListModel(query_service=qs)
    m.refresh()
    assert m.initialized
    m.reset()
    assert not m.initialized
    assert m.count == 0


def test_cancel(qs):
    qe = MagicMock()
    m = TrackListModel(query_service=qs, query_executor=qe)
    m.refresh()
    m.cancel()
    assert m.cancelled


def test_no_query_service():
    m = TrackListModel()
    assert m._fetch_count() == 0
    assert m._fetch_page(0, 10) == []


def test_owner(qs):
    m = TrackListModel(query_service=qs)
    assert m._owner() == "tracks"


def test_empty_state(qs):
    qs.count_tracks.return_value = 0
    qs.fetch_tracks.return_value = []
    m = TrackListModel(query_service=qs)
    m.refresh()
    assert m.empty
