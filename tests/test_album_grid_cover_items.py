"""Tests for AlbumGridWidget with CoverFlowItem — _compute_items_sig, async covers, filters."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from library.album_art import CoverFlowItem
import pytest


@pytest.fixture
def grid(qtbot):
    from library.album_grid import AlbumGridWidget
    w = AlbumGridWidget()
    qtbot.addWidget(w)
    return w


def _make_cover_item(album_key="k1", title="Album", subtitle="Artist",
                     track_count=10, duration=3000, quality_str="lossless",
                     health_status="ok") -> CoverFlowItem:
    summary_mock = MagicMock()
    summary_mock.track_count = track_count
    summary_mock.duration = duration

    quality_mock = MagicMock()
    quality_mock.dominant_quality = quality_str

    health_mock = MagicMock()
    health_mock.status = health_status

    tracks = []
    for i in range(track_count):
        t = MagicMock()
        t.duration = duration / max(track_count, 1)
        t.filepath = f"/m/track_{i}.flac"
        t.title = f"Track {i}"
        t.artist = "Artist"
        t.album = title
        t.albumartist = ""
        t.year = 2024
        t.ext = "flac"
        t.track_number = i + 1
        t.disc_number = 1
        t.sample_rate = 44100
        t.bit_depth = 16
        t.bitrate = 1411
        t.genre = "Rock"
        tracks.append(t)
    item = CoverFlowItem(
        pixmap=MagicMock(),
        title=title,
        subtitle=subtitle,
        data={
            "album_key": album_key,
            "summary": summary_mock,
            "quality": quality_mock,
            "health": health_mock,
            "tracks": tracks,
        },
    )
    return item


def _make_media_item(filepath="/m/s.flac", album="A", artist="X",
                     albumartist="", year=2024, duration=200.0, mtime=1000):
    t = MagicMock(spec=["filepath", "album", "artist", "albumartist", "year", "duration", "mtime"])
    t.filepath = filepath
    t.album = album
    t.artist = artist
    t.albumartist = albumartist
    t.year = year
    t.duration = duration
    t.mtime = mtime
    return t


class TestComputeItemsSig:

    def test_compute_sig_media_items_still_works(self, grid):
        widget = grid
        widget._items = [
            _make_media_item(filepath="/a/1.flac", album="A", artist="X"),
            _make_media_item(filepath="/b/2.flac", album="B", artist="Y"),
        ]
        sig = widget._compute_items_sig()
        assert len(sig) == 2
        assert sig[0] == 2
        sig2 = widget._compute_items_sig()
        assert sig == sig2

    def test_compute_sig_media_items_changes_on_change(self, grid):
        widget = grid
        widget._items = [
            _make_media_item(filepath="/a/1.flac", album="A", artist="X"),
        ]
        sig1 = widget._compute_items_sig()
        widget._items = [
            _make_media_item(filepath="/b/2.flac", album="B", artist="Y"),
        ]
        sig2 = widget._compute_items_sig()
        assert sig1 != sig2

    def test_compute_sig_cover_items_uses_album_key(self, grid):
        widget = grid
        widget._items = [
            _make_cover_item(album_key="k1", title="T1", subtitle="A1", quality_str="lossless"),
        ]
        sig = widget._compute_items_sig()
        assert len(sig) == 2
        assert sig[0] == 1

    def test_compute_sig_changes_when_album_key_changes(self, grid):
        widget = grid
        widget._items = [
            _make_cover_item(album_key="k1", title="T1", subtitle="A1"),
        ]
        sig1 = widget._compute_items_sig()
        widget._items = [
            _make_cover_item(album_key="k2", title="T1", subtitle="A1"),
        ]
        sig2 = widget._compute_items_sig()
        assert sig1 != sig2

    def test_compute_sig_cover_items_without_data_does_not_crash(self, grid):
        widget = grid
        item_without_data = _make_cover_item(album_key="k1")
        item_without_data.data = None
        widget._items = [item_without_data]
        sig = widget._compute_items_sig()
        assert len(sig) == 2

    def test_compute_sig_cover_items_with_missing_summary_quality_health_does_not_crash(self, grid):
        widget = grid
        item = CoverFlowItem(
            pixmap=MagicMock(),
            title="T",
            subtitle="A",
            data={
                "album_key": "k1",
                "tracks": [MagicMock()],
                "summary": None,
                "quality": None,
                "health": None,
            },
        )
        widget._items = [item]
        sig = widget._compute_items_sig()
        assert len(sig) == 2

    def test_compute_sig_mixed_items_all_have_data(self, grid):
        widget = grid
        widget._items = [
            _make_cover_item(album_key="k1"),
            _make_cover_item(album_key="k2"),
        ]
        sig = widget._compute_items_sig()
        assert len(sig) == 2


class TestRebuildGridCoverItems:

    def test_rebuild_grid_with_cover_items_does_not_call_worker_load_covers(self, grid):
        widget = grid
        widget._items = [
            _make_cover_item(album_key="k1", title="T1"),
            _make_cover_item(album_key="k2", title="T2"),
        ]
        widget._worker_mgr = MagicMock()
        widget._rebuild_grid()
        widget._worker_mgr.load_covers.assert_not_called()

    def test_rebuild_grid_with_media_items_calls_worker_load_covers(self, grid):
        from library.album_art import CoverFlowItem
        from PySide6.QtGui import QPixmap

        widget = grid
        widget._items = [
            _make_media_item(filepath="/a/1.flac"),
            _make_media_item(filepath="/b/2.flac"),
        ]
        widget._worker_mgr = MagicMock()

        fake_groups = [
            CoverFlowItem(pixmap=QPixmap(1, 1), title="A", subtitle="X", data={"tracks": []}),
            CoverFlowItem(pixmap=QPixmap(1, 1), title="B", subtitle="Y", data={"tracks": []}),
        ]

        with patch("library.album_grid.load_covers_for_albums", return_value=fake_groups):
            widget._rebuild_grid()
        widget._worker_mgr.load_covers.assert_called_once()

    def test_rebuild_grid_empty_items_does_not_crash(self, grid):
        widget = grid
        widget._items = []
        widget._worker_mgr = MagicMock()
        widget._rebuild_grid()
        widget._worker_mgr.load_covers.assert_not_called()

    def test_set_cover_items_skips_async_cover_load(self, grid):
        widget = grid
        widget._worker_mgr = MagicMock()
        widget.set_cover_items([
            _make_cover_item(album_key="k1", title="T1"),
        ])
        widget._worker_mgr.load_covers.assert_not_called()

    def test_set_cover_items_sets_groups_cache_and_pending_false(self, grid):
        widget = grid
        items = [_make_cover_item(album_key="k1", title="T1")]
        widget.set_cover_items(items)
        assert len(widget._groups_cache) == 1
        assert widget._pending_covers is False

    def test_resize_with_cover_items_does_not_retrigger_cover_loader(self, grid):
        widget = grid
        widget._items = [
            _make_cover_item(album_key="k1", title="T1"),
        ]
        widget._worker_mgr = MagicMock()
        widget._rebuild_grid()
        widget._worker_mgr.load_covers.assert_not_called()


class TestFilterSortWithCoverItems:

    def test_filter_all_returns_all(self, grid):
        widget = grid
        groups = [
            _make_cover_item(album_key="k1", title="A", track_count=10),
            _make_cover_item(album_key="k2", title="B", track_count=1),
        ]
        widget._filter_mode = "all"
        result = widget._apply_filter(groups)
        assert len(result) == 2

    def test_filter_incomplete_with_cover_item_tracks(self, grid):
        widget = grid
        groups = [
            _make_cover_item(album_key="k1", title="A", track_count=1),
            _make_cover_item(album_key="k2", title="B", track_count=5),
        ]
        widget._filter_mode = "incomplete"
        result = widget._apply_filter(groups)
        assert len(result) == 1
        assert result[0].title == "A"

    def test_sort_title_with_cover_items(self, grid):
        widget = grid
        groups = [
            _make_cover_item(album_key="k2", title="Zeta"),
            _make_cover_item(album_key="k1", title="Alpha"),
        ]
        widget._sort_key = "title"
        widget._sort_groups(groups)
        assert groups[0].title == "Alpha"
        assert groups[1].title == "Zeta"

    def test_sort_artist_with_cover_items(self, grid):
        widget = grid
        groups = [
            _make_cover_item(album_key="k2", title="A", subtitle="X"),
            _make_cover_item(album_key="k1", title="B", subtitle="A"),
        ]
        widget._sort_key = "artist"
        widget._sort_groups(groups)
        assert groups[0].subtitle == "A"
        assert groups[1].subtitle == "X"

    def test_sort_tracks_with_cover_items(self, grid):
        widget = grid
        groups = [
            _make_cover_item(album_key="k1", title="A", track_count=2),
            _make_cover_item(album_key="k2", title="B", track_count=10),
        ]
        widget._sort_key = "tracks"
        widget._sort_groups(groups)
        assert groups[0].title == "B"

    def test_context_menu_tracks_from_cover_item(self, grid):
        widget = grid
        widget._groups = [
            _make_cover_item(album_key="k1", title="T1", track_count=3),
        ]
        widget.album_double_clicked = MagicMock()
        widget._handle_context("play", 0)
        assert widget.album_double_clicked.emit.called

    def test_handle_context_out_of_range_does_not_crash(self, grid):
        widget = grid
        widget._groups = []
        widget._handle_context("play", 5)
