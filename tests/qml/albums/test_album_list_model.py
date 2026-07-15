from __future__ import annotations
"""Tests for AlbumListModel — 10+ tests."""

from unittest.mock import MagicMock

import pytest

from ui_qml.models.AlbumListModel import AlbumListModel
pytestmark = [pytest.mark.qml_module("album_views")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_albums.return_value = 5
    qs.fetch_albums.return_value = [
        {"album_key": "k1", "title": "A", "artist": "X", "year": 2000,
         "track_count": 10, "duration": 3600, "cover_key": "c1"},
        {"album_key": "k2", "title": "B", "artist": "Y", "year": 2001,
         "track_count": 8, "duration": 2400, "cover_key": "c2"},
    ]
    return qs


def test_initial_state(qs):
    m = AlbumListModel(query_service=qs)
    assert m.count == 0
    assert m.totalCount == 0
    assert not m.loading
    assert not m.initialized


def test_refresh_loads_data(qs):
    m = AlbumListModel(query_service=qs)
    m.refresh()
    assert m.count == 2
    assert m.totalCount == 5
    assert m.initialized


def test_role_names(qs):
    m = AlbumListModel(query_service=qs)
    roles = m.roleNames()
    assert b"albumKey" in roles.values()
    assert b"title" in roles.values()
    assert b"artist" in roles.values()
    assert b"year" in roles.values()
    assert b"trackCount" in roles.values()
    assert b"duration" in roles.values()
    assert b"coverKey" in roles.values()


def test_data_access(qs):
    m = AlbumListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, m.TitleRole) == "A"
    assert m.data(idx, m.ArtistRole) == "X"
    assert m.data(idx, m.YearRole) == 2000
    assert m.data(idx, m.TrackCountRole) == 10
    assert m.data(idx, m.DurationRole) == 3600
    assert m.data(idx, m.CoverKeyRole) == "c1"


def test_data_returns_none_for_invalid(qs):
    m = AlbumListModel(query_service=qs)
    assert m.data(m.index(999, 0)) is None


def test_has_more(qs):
    m = AlbumListModel(query_service=qs, page_size=1)
    qs.count_albums.return_value = 10
    qs.fetch_albums.return_value = [{"album_key": "k1", "title": "A"}]
    m.refresh()
    assert m.hasMore


def test_fetch_more(qs):
    qe = MagicMock()
    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        items = task()
        on_success(items)
        return 1
    qe.submit.side_effect = submit_side
    m = AlbumListModel(query_service=qs, page_size=2, query_executor=qe)
    qs.count_albums.return_value = 4
    qs.fetch_albums.side_effect = [
        [{"album_key": "k1", "title": "A"}, {"album_key": "k2", "title": "B"}],
        [{"album_key": "k3", "title": "C"}, {"album_key": "k4", "title": "D"}],
    ]
    m.refresh()
    assert m.count == 2
    assert m.canFetchMore()
    m.fetchMore()
    assert m.count == 4
    assert not m.canFetchMore()


def test_reset(qs):
    m = AlbumListModel(query_service=qs)
    m.refresh()
    assert m.initialized
    m.reset()
    assert m.count == 0
    assert not m.initialized


def test_cancel(qs):
    m = AlbumListModel(query_service=qs, query_executor=MagicMock())
    m.refresh()
    m.cancel()
    assert m.cancelled


def test_owner(qs):
    m = AlbumListModel(query_service=qs)
    assert m._owner() == "albums"


def test_fetch_count_no_qs(qs):
    m = AlbumListModel()
    assert m._fetch_count() == 0


def test_fetch_page_no_qs(qs):
    m = AlbumListModel()
    assert m._fetch_page(0, 10) == []


def test_empty_after_refresh(qs):
    qs.count_albums.return_value = 0
    qs.fetch_albums.return_value = []
    m = AlbumListModel(query_service=qs)
    assert m.empty
    m.refresh()
    assert m.empty
