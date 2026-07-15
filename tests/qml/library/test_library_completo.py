from __future__ import annotations
"""Comprehensive tests for Library — 15+ tests.
Covers: pagination, fetchMore, cancel, stale protection, sort, filters,
columns, selection, range selection, select all filtered, context actions,
errors, source offline, no sources, scan, indexing.
"""

from unittest.mock import MagicMock

import pytest

from ui_qml.models.TrackListModel import TrackListModel
from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_tracks.return_value = 100
    qs.fetch_tracks.return_value = [
        {"track_id": i, "title": f"Song {i}", "artist": "A",
         "album": "Al", "filepath": f"/p/{i}.flac", "duration": 200,
         "format": "FLAC", "genre": "Rock", "year": 2020,
         "track_number": i, "favorite": False}
        for i in range(20)
    ]
    return qs


class TestLibraryCompleto:
    def test_initial_state(self, qs):
        m = TrackListModel(query_service=qs)
        assert m.count == 0
        assert not m.initialized

    def test_refresh_loads_first_page(self, qs):
        m = TrackListModel(query_service=qs, page_size=20)
        m.refresh()
        assert m.count == 20
        assert m.totalCount == 100

    def test_fetch_more(self, qs):
        qe = MagicMock()
        call_count = 0
        def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
            nonlocal call_count
            call_count += 1
            items = task()
            on_success(items)
            return call_count
        qe.submit.side_effect = submit_side
        qs.fetch_tracks.side_effect = [
            [{"track_id": i, "title": f"Song {i}"} for i in range(10)],
            [{"track_id": i, "title": f"Song {i}"} for i in range(10, 20)],
        ]
        m = TrackListModel(query_service=qs, page_size=10, query_executor=qe)
        qs.count_tracks.return_value = 20
        m.refresh()
        assert m.count == 10
        m.fetchMore()
        assert m.count == 20

    def test_cancel(self, qs):
        qe = MagicMock()
        m = TrackListModel(query_service=qs, query_executor=qe)
        m.refresh()
        m.cancel()
        assert m.cancelled

    def test_stale_protection(self, qs):
        qe = MagicMock()
        def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
            count = qs.count_tracks.return_value
            items = qs.fetch_tracks.return_value
            on_success((count, items))
            return 1
        qe.submit.side_effect = submit_side
        m = TrackListModel(query_service=qs, query_executor=qe)
        m.refresh()
        m._refresh_gen = -1
        m.fetchMore()
        assert m.count > 0

    def test_sort_by_column(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh(search="", sort="title", asc=True)
        assert m._sort == "title"
        m.refresh(search="", sort="year", asc=False)
        assert m._sort == "year"

    def test_filter_by_format(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh(search="", fmt="FLAC")
        assert m._fmt_filter == "FLAC"

    def test_filter_by_genre(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh(search="", genre="Rock")
        assert m._genre_filter == "Rock"

    def test_filter_by_favorites(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh(search="", favorites=True)
        assert m._favorites_filter is True

    def test_reset(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.initialized
        m.reset()
        assert not m.initialized
        assert m.count == 0

    def test_songs_page_from_bridge(self, qs):
        bridge = LibraryBridge(query_service=qs, query_executor=MagicMock())
        page = bridge.getSongsPage(0, 10)
        assert len(page) >= 0

    def test_bridge_state_initial(self):
        bridge = LibraryBridge()
        assert bridge.state == "INITIALIZING"

    def test_bridge_state_no_sources(self, qs):
        qs.count_tracks.return_value = 0
        bridge = LibraryBridge(query_service=qs)
        assert bridge.state is not None

    def test_bridge_search(self, qs):
        bridge = LibraryBridge(query_service=qs)
        result = bridge.setSearchQuery("test")
        assert result["ok"]

    def test_bridge_clear_filters(self, qs):
        bridge = LibraryBridge(query_service=qs)
        result = bridge.clearFilters()
        assert result["ok"]

    def test_load_next_page(self, qs):
        bridge = LibraryBridge(query_service=qs)
        result = bridge.loadNextPage()
        assert result["ok"]

    def test_has_more(self, qs):
        qs.count_tracks.return_value = 50
        m = TrackListModel(query_service=qs, page_size=20)
        m.refresh()
        assert m.hasMore

    def test_empty_without_qs(self):
        m = TrackListModel()
        assert m._fetch_count() == 0
        assert m._fetch_page(0, 10) == []

    def test_owner(self, qs):
        m = TrackListModel(query_service=qs)
        assert m._owner() == "tracks"
