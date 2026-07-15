from __future__ import annotations
"""Comprehensive tests for Artists — 12+ tests."""

from unittest.mock import MagicMock

import pytest

from ui_qml.models.ArtistListModel import ArtistListModel
pytestmark = [pytest.mark.qml_module("album_views")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_artists.return_value = 5
    qs.fetch_artists.return_value = [
        {"name": "Artist A", "track_count": 50, "album_count": 5, "cover_key": "c_a",
         "genre": "Rock", "aliases": "A.K.A.", "is_album_artist": True},
        {"name": "Artist B", "track_count": 30, "album_count": 3, "cover_key": "c_b",
         "genre": "Jazz", "aliases": "", "is_album_artist": False},
    ]
    return qs


class TestArtistsCompleto:
    def test_initial_state(self, qs):
        m = ArtistListModel(query_service=qs)
        assert m.count == 0
        assert not m.initialized

    def test_refresh_loads(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh()
        assert m.count == 2
        assert m.totalCount == 5

    def test_role_names(self, qs):
        m = ArtistListModel(query_service=qs)
        roles = m.roleNames()
        for expected in [b"name", b"trackCount", b"albumCount", b"coverKey"]:
            assert expected in roles.values()

    def test_data_access(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, m.NameRole) == "Artist A"
        assert m.data(idx, m.TrackCountRole) == 50
        assert m.data(idx, m.AlbumCountRole) == 5
        assert m.data(idx, m.CoverKeyRole) == "c_a"

    def test_second_artist(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh()
        idx = m.index(1, 0)
        assert m.data(idx, m.NameRole) == "Artist B"
        assert m.data(idx, m.TrackCountRole) == 30
        assert m.data(idx, m.AlbumCountRole) == 3

    def test_display_role(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, 0) == "Artist A"

    def test_has_more(self, qs):
        m = ArtistListModel(query_service=qs, page_size=1)
        qs.count_artists.return_value = 5
        qs.fetch_artists.return_value = [{"name": "A"}]
        m.refresh()
        assert m.hasMore

    def test_fetch_more(self, qs):
        qe = MagicMock()
        def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
            items = task()
            on_success(items)
            return 1
        qe.submit.side_effect = submit_side
        m = ArtistListModel(query_service=qs, page_size=1, query_executor=qe)
        qs.count_artists.return_value = 3
        qs.fetch_artists.side_effect = [
            [{"name": "A"}],
            [{"name": "B"}],
        ]
        m.refresh()
        assert m.count == 1
        m.fetchMore()
        assert m.count == 2

    def test_empty_without_qs(self):
        m = ArtistListModel()
        assert m._fetch_count() == 0
        assert m._fetch_page(0, 10) == []

    def test_cancel(self, qs):
        qe = MagicMock()
        m = ArtistListModel(query_service=qs, query_executor=qe)
        m.refresh()
        m.cancel()
        assert m.cancelled

    def test_reset(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh()
        assert m.initialized
        m.reset()
        assert not m.initialized
        assert m.count == 0

    def test_owner(self, qs):
        m = ArtistListModel(query_service=qs)
        assert m._owner() == "artists"

    def test_sort_and_search(self, qs):
        m = ArtistListModel(query_service=qs)
        m.refresh(search="test", sort="name", asc=True)
        assert m._qs is not None
