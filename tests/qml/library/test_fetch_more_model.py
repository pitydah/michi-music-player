"""Tests for fetchMore behavior in BasePagedListModel and TrackListModel."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication


class MockExecutor:
    def __init__(self):
        self._counter = 0

    def submit(self, owner, task, on_success=None, on_error=None, on_cancelled=None, supersede=False):
        self._counter += 1
        try:
            result = task()
            if on_success:
                on_success(result)
        except Exception as e:
            if on_error:
                on_error("ERROR", str(e))
        return self._counter

    def cancel(self, request_id):
        pass


class TestFetchMoreModel:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    def _make_model(self, total=50):
        from ui_qml.models.TrackListModel import TrackListModel
        executor = MockExecutor()
        qs = MagicMock()
        qs.count_tracks.return_value = total

        def fetch_page(offset=0, limit=250, **kw):
            remaining = max(0, total - offset)
            count = min(limit, remaining)
            return [{"track_id": offset + i + 1, "title": f"Track {offset + i + 1}",
                     "artist": "Test", "album": "Test Album", "duration": 200,
                     "format": "FLAC", "year": 2024, "genre": "Test",
                     "track_number": i + 1, "favorite": False, "missing": False,
                     "bit_depth": 24, "bitrate": 96000}
                    for i in range(count)]

        qs.fetch_tracks.side_effect = fetch_page
        model = TrackListModel(query_service=qs, query_executor=executor, page_size=10)
        return model, qs, executor

    def test_initial_has_more(self):
        model, qs, _ = self._make_model(total=50)
        model.refresh()
        assert model.hasMore is True
        assert model.count == 10

    def test_fetch_more_appends(self):
        model, qs, _ = self._make_model(total=50)
        model.refresh()
        c1 = model.count
        model.fetchMore()
        assert model.count > c1

    def test_fetch_more_eventually_exhausts(self):
        model, qs, _ = self._make_model(total=25)
        model._page_size = 10
        model.refresh()
        for _ in range(5):
            if not model.hasMore:
                break
            model.fetchMore()
        assert model.hasMore is False or model.count == 25

    def test_loading_more_flag(self):
        model, qs, _ = self._make_model(total=50)
        model.refresh()
        assert model.loadingMore is False

    def test_can_fetch_more(self):
        model, qs, _ = self._make_model(total=50)
        model.refresh()
        assert model.canFetchMore() is True

    def test_small_dataset_no_fetch_more(self):
        model, qs, _ = self._make_model(total=5)
        model._page_size = 10
        model.refresh()
        assert model.hasMore is False
        assert model.canFetchMore() is False

    def test_error_state(self):
        from ui_qml.models.TrackListModel import TrackListModel
        executor = MockExecutor()
        qs = MagicMock()
        qs.count_tracks.side_effect = Exception("DB error")
        model = TrackListModel(query_service=qs, query_executor=executor, page_size=10)
        model.refresh()
        assert model.errorCode != "" or model.errorMessage != ""

    def test_id_at_slot(self):
        model, qs, _ = self._make_model(total=10)
        model._page_size = 10
        model.refresh()
        assert model.idAt(0) == 1
        assert model.idAt(5) == 6
        assert model.idAt(99) == -1

    def test_reset_clears_state(self):
        model, qs, _ = self._make_model(total=50)
        model.refresh()
        assert model.count > 0
        model.reset()
        assert model.count == 0
        assert model.initialized is False
