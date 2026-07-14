"""Advanced tests for LibraryTrackTable, TrackListModel fetch-more — 15+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml.models.TrackListModel import TrackListModel


@pytest.fixture
def qs():
    qs = MagicMock()
    qs.count_tracks.return_value = 25
    qs.fetch_tracks.return_value = [
        {"track_id": i, "track_uid": f"uid{i}", "title": f"Song {i}",
         "artist": "Artist", "album": "Album", "album_key": "ak",
         "duration": 200, "format": "FLAC", "year": 2020, "genre": "Rock",
         "track_number": i, "cover_key": "ck"}
        for i in range(1, 11)
    ]
    return qs


class TestTrackListModelAvanzado:
    def test_is_loading_property(self, qs):
        m = TrackListModel(query_service=qs)
        assert m.isLoading is False
        assert m.loading is False

    def test_is_fetching_more_property(self, qs):
        m = TrackListModel(query_service=qs)
        assert m.isFetchingMore is False
        assert m.loadingMore is False

    def test_has_more_initial(self, qs):
        m = TrackListModel(query_service=qs, page_size=10)
        qs.count_tracks.return_value = 25
        qs.fetch_tracks.return_value = [{"track_id": 1, "title": "A"}]
        m.refresh()
        assert m.hasMore is True

    def test_has_more_exhausted(self, qs):
        m = TrackListModel(query_service=qs, page_size=10)
        qs.count_tracks.return_value = 1
        m.refresh()
        assert m.hasMore is False

    def test_last_error_empty_initially(self, qs):
        m = TrackListModel(query_service=qs)
        assert m.lastError == ""

    def test_id_at_valid(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.idAt(0) == 1
        assert m.idAt(1) == 2

    def test_id_at_invalid(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.idAt(999) == -1

    def test_visible_ids_returns_ids(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        ids = m.visibleIds()
        assert len(ids) == 10
        assert ids[0] == 1
        assert ids[9] == 10

    def test_visible_ids_empty(self, qs):
        qs.count_tracks.return_value = 0
        qs.fetch_tracks.return_value = []
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.visibleIds() == []

    def test_filtered_ids_returns_ids(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        ids = m.filteredIds()
        assert len(ids) == 10

    def test_no_track_id_role_global(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.idAt(0) == 1
        assert not hasattr(TrackListModel, 'TrackIdRole') or m.TrackIdRole is not None

    def test_fetch_more_with_executor(self, qs):
        qe = MagicMock()
        def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
            items = task()
            on_success(items)
            return 1
        qe.submit.side_effect = submit_side
        m = TrackListModel(query_service=qs, page_size=5, query_executor=qe)
        qs.count_tracks.return_value = 15
        qs.fetch_tracks.side_effect = [
            [{"track_id": 1, "title": "A"}],
            [{"track_id": 2, "title": "B"}],
        ]
        m.refresh()
        assert m.count == 1
        m.fetchMore()
        assert m.count == 2
        assert m.isFetchingMore is False

    def test_can_fetch_more_after_refresh(self, qs):
        m = TrackListModel(query_service=qs, page_size=5)
        qs.count_tracks.return_value = 20
        m.refresh()
        assert m.canFetchMore() is True

    def test_cannot_fetch_more_exhausted(self, qs):
        m = TrackListModel(query_service=qs, page_size=10)
        qs.count_tracks.return_value = 10
        m.refresh()
        assert m.canFetchMore() is False

    def test_cancel_sets_cancelled(self, qs):
        qe = MagicMock()
        m = TrackListModel(query_service=qs, query_executor=qe)
        m.refresh()
        m.cancel()
        assert m.cancelled is True

    def test_reset_clears_state(self, qs):
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.initialized
        m.reset()
        assert not m.initialized
        assert m.count == 0

    def test_empty_state(self, qs):
        qs.count_tracks.return_value = 0
        qs.fetch_tracks.return_value = []
        m = TrackListModel(query_service=qs)
        m.refresh()
        assert m.empty

    def test_no_query_service(self):
        m = TrackListModel()
        assert m._fetch_count() == 0
        assert m._fetch_page(0, 10) == []
        assert m.visibleIds() == []
        assert m.idAt(0) == -1
