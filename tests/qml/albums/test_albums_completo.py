from __future__ import annotations
"""Comprehensive tests for Albums — 12+ tests."""

from unittest.mock import MagicMock

import pytest

from ui_qml.models.AlbumPagedListModel import AlbumPagedListModel
pytestmark = [pytest.mark.qml_module("album_views")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_albums.return_value = 5
    qs.fetch_albums.return_value = [
        {"album_key": "k1", "title": "Alpha", "artist": "X", "year": 2000,
         "genre": "Rock", "track_count": 10, "disc_count": 2, "duration": 3600,
         "cover_key": "c1", "artist_id": 1, "album_artist": "X",
         "formats": "FLAC", "max_quality": "24bit", "last_played": "",
         "date_added": "2024-01-01", "favorite": True, "compilation": False,
         "missing_count": 1},
        {"album_key": "k2", "title": "Beta", "artist": "Y", "year": 2001,
         "genre": "Jazz", "track_count": 8, "disc_count": 1, "duration": 2400,
         "cover_key": "c2", "artist_id": 2, "album_artist": "Y",
         "formats": "MP3", "max_quality": "320kbps", "last_played": "2024-06-01",
         "date_added": "2024-02-01", "favorite": False, "compilation": True,
         "missing_count": 0},
    ]
    return qs


class TestAlbumsCompleto:
    def test_initial_state(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        assert m.count == 0

    def test_refresh_loads(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        assert m.count == 2
        assert m.totalCount == 5

    def test_album_roles(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, m.TitleRole) == "Alpha"
        assert m.data(idx, m.ArtistRole) == "X"
        assert m.data(idx, m.DiscCountRole) == 2
        assert m.data(idx, m.CompilationRole) is False
        assert m.data(idx, m.FavoriteRole) is True

    def test_multi_disc_album(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, m.DiscCountRole) == 2
        idx2 = m.index(1, 0)
        assert m.data(idx2, m.DiscCountRole) == 1

    def test_compilation_flag(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        assert m.data(m.index(0, 0), m.CompilationRole) is False
        assert m.data(m.index(1, 0), m.CompilationRole) is True

    def test_second_album_fields(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        idx = m.index(1, 0)
        assert m.data(idx, m.TitleRole) == "Beta"
        assert m.data(idx, m.GenreRole) == "Jazz"
        assert m.data(idx, m.YearRole) == 2001

    def test_album_detail_roles_complete(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, m.CoverKeyRole) == "c1"
        assert m.data(idx, m.ArtistIdRole) == 1
        assert m.data(idx, m.AlbumArtistRole) == "X"
        assert m.data(idx, m.FormatsRole) == "FLAC"
        assert m.data(idx, m.MaxQualityRole) == "24bit"

    def test_display_role(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        idx = m.index(0, 0)
        assert m.data(idx, 0) == "Alpha"

    def test_has_more(self, qs):
        m = AlbumPagedListModel(query_service=qs, page_size=1)
        qs.count_albums.return_value = 5
        qs.fetch_albums.return_value = [{"album_key": "k1", "title": "A"}]
        m.refresh()
        assert m.hasMore

    def test_fetch_more(self, qs):
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
        m.fetchMore()
        assert m.count == 2

    def test_empty_without_qs(self):
        m = AlbumPagedListModel()
        assert m._fetch_count() == 0
        assert m._fetch_page(0, 10) == []

    def test_cancel(self, qs):
        qe = MagicMock()
        m = AlbumPagedListModel(query_service=qs, query_executor=qe)
        m.refresh()
        m.cancel()
        assert m.cancelled

    def test_reset(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        m.refresh()
        assert m.initialized
        m.reset()
        assert not m.initialized
        assert m.count == 0

    def test_back_state_via_owner(self, qs):
        m = AlbumPagedListModel(query_service=qs)
        assert m._owner() == "album_paged"
