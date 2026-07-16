"""Tests for SongGridWidget with status badges."""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest


@pytest.fixture
def grid(qtbot):
    from library.song_grid import SongGridWidget
    w = SongGridWidget()
    qtbot.addWidget(w)
    return w


def _make_item(title="Song", artist="Artist", album="Album", ext="flac",
               filepath="/m/s.flac", duration=200, id=1):
    item = MagicMock()
    item.title = title
    item.artist = artist
    item.album = album
    item.ext = ext
    item.filepath = filepath
    item.duration = duration
    item.id = id
    return item


class TestSongGridBadges:

    def test_set_items_with_status_cache(self, grid):
        items = [_make_item(id=1, title="A"), _make_item(id=2, title="B")]
        status_cache = {
            1: {"is_favorite": True, "quality_category": "lossless"},
            2: {"is_favorite": False, "quality_category": "hires"},
        }
        grid.set_items(items, status_cache=status_cache)
        assert len(grid._items) == 2

    def test_empty_items_does_not_crash(self, grid):
        grid.set_items([])
        assert grid._items == []

    def test_card_created_with_status_favorite(self, grid):
        items = [_make_item(id=1, title="A")]
        status_cache = {1: {"is_favorite": True, "quality_category": "lossless"}}
        grid.set_items(items, status_cache=status_cache)
        assert grid._grid.count() == 1
        card = grid._grid.itemAt(0).widget()
        assert card._status.get("is_favorite") is True

    def test_card_created_with_status_hires(self, grid):
        items = [_make_item(id=1, title="A")]
        status_cache = {1: {"is_favorite": False, "quality_category": "hires"}}
        grid.set_items(items, status_cache=status_cache)
        assert grid._grid.count() == 1

    def test_card_with_audio_lab_warning(self, grid):
        items = [_make_item(id=1, title="A")]
        status_cache = {1: {"is_favorite": False, "has_audio_lab_warning": True}}
        grid.set_items(items, status_cache=status_cache)
        assert grid._grid.count() == 1

    def test_double_click_emits_filepath(self, grid):
        items = [_make_item(id=1, title="A", filepath="/s/s.flac")]
        grid.set_items(items)
        received = []

        def handler(fp):
            received.append(fp)

        grid.song_double_clicked.connect(handler)
        card = grid._grid.itemAt(0).widget()
        card.double_clicked.emit("/s/s.flac")
        assert received == ["/s/s.flac"]
