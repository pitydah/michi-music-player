from __future__ import annotations
"""Tests for AlbumDetailPage and AlbumPagedListModel — 12+ tests."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from ui_qml.models.AlbumPagedListModel import AlbumPagedListModel
pytestmark = [pytest.mark.qml_module("album_views")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_albums.return_value = 3
    qs.fetch_albums.return_value = [
        {"album_key": "k1", "title": "Alpha", "artist": "X", "year": 2000,
         "genre": "Rock", "track_count": 10, "disc_count": 1, "duration": 3600,
         "cover_key": "c1", "artist_id": 1, "album_artist": "X",
         "formats": "FLAC", "max_quality": "24bit", "last_played": "",
         "date_added": "2024-01-01", "favorite": True, "compilation": False},
        {"album_key": "k2", "title": "Beta", "artist": "Y", "year": 2001,
         "genre": "Jazz", "track_count": 8, "disc_count": 1, "duration": 2400,
         "cover_key": "c2", "artist_id": 2, "album_artist": "Y",
         "formats": "MP3", "max_quality": "320kbps", "last_played": "2024-06-01",
         "date_added": "2024-02-01", "favorite": False, "compilation": True},
    ]
    return qs


def test_album_detail_initial_state(qs):
    m = AlbumPagedListModel(query_service=qs)
    assert m.count == 0
    assert not m.initialized


def test_album_detail_refresh(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    assert m.count == 2
    assert m.totalCount == 3


def test_album_detail_role_names(qs):
    m = AlbumPagedListModel(query_service=qs)
    roles = m.roleNames()
    for expected in [b"albumKey", b"title", b"artist", b"year", b"genre",
                     b"trackCount", b"discCount", b"duration", b"coverKey",
                     b"artistId", b"albumArtist", b"formats", b"maxQuality",
                     b"lastPlayed", b"dateAdded", b"favorite", b"compilation"]:
        assert expected in roles.values()


def test_album_detail_all_roles(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, m.TitleRole) == "Alpha"
    assert m.data(idx, m.ArtistRole) == "X"
    assert m.data(idx, m.YearRole) == 2000
    assert m.data(idx, m.GenreRole) == "Rock"
    assert m.data(idx, m.TrackCountRole) == 10
    assert m.data(idx, m.DiscCountRole) == 1
    assert m.data(idx, m.DurationRole) == 3600
    assert m.data(idx, m.CoverKeyRole) == "c1"
    assert m.data(idx, m.ArtistIdRole) == 1
    assert m.data(idx, m.AlbumArtistRole) == "X"
    assert m.data(idx, m.FormatsRole) == "FLAC"
    assert m.data(idx, m.MaxQualityRole) == "24bit"
    assert m.data(idx, m.FavoriteRole) is True
    assert m.data(idx, m.CompilationRole) is False


def test_album_detail_second_album(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    idx = m.index(1, 0)
    assert m.data(idx, m.TitleRole) == "Beta"
    assert m.data(idx, m.CompilationRole) is True
    assert m.data(idx, m.FavoriteRole) is False
    assert m.data(idx, m.LastPlayedRole) == "2024-06-01"


def test_album_detail_empty_without_qs():
    m = AlbumPagedListModel()
    assert m._fetch_count() == 0
    assert m._fetch_page(0, 10) == []


def test_album_detail_cancel(qs):
    m = AlbumPagedListModel(query_service=qs, query_executor=MagicMock())
    m.refresh()
    m.cancel()
    assert m.cancelled


def test_album_detail_reset(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    assert m.initialized
    m.reset()
    assert not m.initialized
    assert m.count == 0


def test_album_detail_has_more(qs):
    m = AlbumPagedListModel(query_service=qs, page_size=1)
    qs.count_albums.return_value = 5
    qs.fetch_albums.return_value = [{"album_key": "k1", "title": "A"}]
    m.refresh()
    assert m.hasMore


def test_album_detail_fetch_more(qs):
    qe = MagicMock()
    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        items = task()
        on_success(items)
        return 1
    qe.submit.side_effect = submit_side
    m = AlbumPagedListModel(query_service=qs, page_size=1, query_executor=qe)
    qs.count_albums.return_value = 3
    qs.fetch_albums.side_effect = [
        [{"album_key": "k1", "title": "A"}],
        [{"album_key": "k2", "title": "B"}],
    ]
    m.refresh()
    assert m.count == 1
    assert m.canFetchMore()
    m.fetchMore()
    assert m.count == 2


def test_album_detail_display_role(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, Qt.DisplayRole) == "Alpha"


def test_album_detail_invalid_index(qs):
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    assert m.data(m.index(999, 0)) is None


def test_album_detail_owner(qs):
    m = AlbumPagedListModel(query_service=qs)
    assert m._owner() == "album_paged"


def test_album_detail_empty_state(qs):
    qs.count_albums.return_value = 0
    qs.fetch_albums.return_value = []
    m = AlbumPagedListModel(query_service=qs)
    m.refresh()
    assert m.empty
