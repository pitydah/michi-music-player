from __future__ import annotations
"""Tests for ArtistListModel — 10+ tests."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from ui_qml.models.ArtistListModel import ArtistListModel
pytestmark = [pytest.mark.qml_module("album_views")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_artists.return_value = 5
    qs.fetch_artists.return_value = [
        {"name": "Artist A", "track_count": 20, "album_count": 3, "cover_key": "ca1"},
        {"name": "Artist B", "track_count": 15, "album_count": 2, "cover_key": "ca2"},
    ]
    return qs


def test_initial_state(qs):
    m = ArtistListModel(query_service=qs)
    assert m.count == 0
    assert not m.loading
    assert not m.initialized


def test_refresh_loads_data(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    assert m.count == 2
    assert m.totalCount == 5
    assert m.initialized


def test_role_names(qs):
    m = ArtistListModel(query_service=qs)
    roles = m.roleNames()
    assert b"name" in roles.values()
    assert b"trackCount" in roles.values()
    assert b"albumCount" in roles.values()
    assert b"coverKey" in roles.values()


def test_data_access(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, m.NameRole) == "Artist A"
    assert m.data(idx, m.TrackCountRole) == 20
    assert m.data(idx, m.AlbumCountRole) == 3
    assert m.data(idx, m.CoverKeyRole) == "ca1"


def test_data_role_mapping(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    idx = m.index(1, 0)
    assert m.data(idx, m.NameRole) == "Artist B"
    assert m.data(idx, m.TrackCountRole) == 15


def test_display_role(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    idx = m.index(0, 0)
    assert m.data(idx, Qt.DisplayRole) == "Artist A"


def test_invalid_index(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    assert m.data(m.index(999, 0)) is None


def test_has_more(qs):
    m = ArtistListModel(query_service=qs, page_size=1)
    qs.count_artists.return_value = 10
    qs.fetch_artists.return_value = [{"name": "A"}]
    m.refresh()
    assert m.hasMore


def test_fetch_more(qs):
    qe = MagicMock()
    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        items = task()
        on_success(items)
        return 1
    qe.submit.side_effect = submit_side
    m = ArtistListModel(query_service=qs, page_size=2, query_executor=qe)
    qs.count_artists.return_value = 4
    qs.fetch_artists.side_effect = [
        [{"name": "A"}, {"name": "B"}],
        [{"name": "C"}, {"name": "D"}],
    ]
    m.refresh()
    assert m.count == 2
    assert m.canFetchMore()
    m.fetchMore()
    assert m.count == 4
    assert not m.canFetchMore()


def test_reset(qs):
    m = ArtistListModel(query_service=qs)
    m.refresh()
    assert m.initialized
    m.reset()
    assert m.count == 0
    assert not m.initialized


def test_cancel(qs):
    m = ArtistListModel(query_service=qs, query_executor=MagicMock())
    m.refresh()
    m.cancel()
    assert m.cancelled


def test_no_query_service():
    m = ArtistListModel()
    assert m._fetch_count() == 0
    assert m._fetch_page(0, 10) == []


def test_owner(qs):
    m = ArtistListModel(query_service=qs)
    assert m._owner() == "artists"


def test_empty_state(qs):
    qs.count_artists.return_value = 0
    qs.fetch_artists.return_value = []
    m = ArtistListModel(query_service=qs)
    m.refresh()
    assert m.empty
