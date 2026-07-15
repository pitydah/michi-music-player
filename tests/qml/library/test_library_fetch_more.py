"""Tests for LibraryTrackTable fetchMore behavior — 6+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml.models.TrackListModel import TrackListModel
import pytest
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def make_qs(count=10, page_size=3):
    qs = MagicMock()
    qs.count_tracks.return_value = count

    def fetch_side(offset=0, limit=page_size, **kw):
        remaining = count - offset
        actual = min(limit, remaining)
        return [
            {"track_id": offset + i + 1, "title": f"Song {offset + i + 1}",
             "artist": "A", "album": "B", "album_key": "bk",
             "duration": 200, "format": "FLAC"}
            for i in range(actual)
        ]

    qs.fetch_tracks.side_effect = fetch_side
    return qs


def test_fetch_more_basic():
    qs = make_qs(10, 3)
    qe = MagicMock()

    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        result = task()
        on_success(result)
        return 1

    qe.submit.side_effect = submit_side
    m = TrackListModel(page_size=3, query_service=qs, query_executor=qe)
    m.refresh()
    assert m.count == 3
    assert m.hasMore is True

    m.fetchMore()
    assert m.count == 6

    m.fetchMore()
    assert m.count == 9

    m.fetchMore()
    assert m.count == 10


def test_fetch_more_complete():
    qs = make_qs(3, 5)
    qe = MagicMock()

    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        result = task()
        on_success(result)
        return 1

    qe.submit.side_effect = submit_side
    m = TrackListModel(page_size=5, query_service=qs, query_executor=qe)
    m.refresh()
    assert m.count == 3
    assert m.hasMore is False


def test_can_fetch_more():
    qs = make_qs(10, 3)
    qe = MagicMock()

    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        result = task()
        on_success(result)
        return 1

    qe.submit.side_effect = submit_side
    m = TrackListModel(page_size=3, query_service=qs, query_executor=qe)
    m.refresh()
    assert m.canFetchMore() is True
    m.fetchMore()
    assert m.canFetchMore() is True
    m.fetchMore()
    m.fetchMore()
    assert m.canFetchMore() is False


def test_fetch_more_during_loading(app):
    qs = make_qs(10, 3)
    qe = MagicMock()

    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        result = task()
        on_success(result)
        return 1

    qe.submit.side_effect = submit_side
    m = TrackListModel(page_size=3, query_service=qs, query_executor=qe)
    m.refresh()
    assert m.count == 3

    m._loading_more = True
    m.loadingMoreChanged.emit()
    m.fetchMore()
    assert m.count == 3


def test_fetch_more_after_dispose():
    qs = make_qs(10, 3)
    qe = MagicMock()
    m = TrackListModel(page_size=3, query_service=qs, query_executor=qe)
    m.dispose()
    m.fetchMore()
    assert m.count == 0


def test_fetch_more_data_integrity():
    qs = make_qs(10, 3)
    qe = MagicMock()

    def submit_side(owner, task, on_success, on_error, on_cancelled, supersede=False):
        result = task()
        on_success(result)
        return 1

    qe.submit.side_effect = submit_side
    m = TrackListModel(page_size=3, query_service=qs, query_executor=qe)
    m.refresh()

    idx0 = m.index(0, 0)
    assert m.data(idx0, m.TitleRole) == "Song 1"

    m.fetchMore()
    idx3 = m.index(3, 0)
    assert m.data(idx3, m.TitleRole) == "Song 4"
