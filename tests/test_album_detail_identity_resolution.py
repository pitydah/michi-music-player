"""Tests for show_album_detail_from_cover_item fallback resolution."""
from __future__ import annotations

from unittest.mock import MagicMock

from library.album_art import _CoverFlowItemLegacy as CoverFlowItem
from library.album_repository import AlbumGroup
from library.album_identity import AlbumIdentity


def _make_track(album="A", artist="X", filepath="/m/s.flac",
                ext="flac", duration=200.0, year=2024):
    t = MagicMock()
    t.album = album
    t.artist = artist
    t.filepath = filepath
    t.title = "Song"
    t.duration = duration
    t.year = year
    t.ext = ext
    t.track_number = 1
    t.disc_number = 1
    t.sample_rate = 44100
    t.bit_depth = 16
    t.bitrate = 1411
    t.genre = "Rock"
    return t


def _fake_cover_item(album_key="k1", title="Album", subtitle="Artist",
                     tracks=None, album_group=None):
    if tracks is None:
        tracks = [_make_track()]
    data = {
        "album_key": album_key,
        "tracks": tracks,
        "album_group": album_group,
    }
    return CoverFlowItem(
        pixmap=MagicMock(),
        title=title,
        subtitle=subtitle,
        data=data,
    )


def _fake_group(title="Album", artist="Artist", album_key="k1", tracks=None):
    identity = AlbumIdentity(
        album_key=album_key,
        display_title=title,
        display_artist=artist,
    )
    tracks = tracks or [_make_track()]
    g = AlbumGroup(identity=identity, tracks=tracks)
    return g


def _make_window_with_repo(groups_dict=None):
    w = MagicMock()
    w._nav_ctrl = MagicMock()
    if groups_dict:
        repo = MagicMock()
        def get_group(k):
            return groups_dict.get(k)
        repo.get_group = get_group
        w._album_data_repo = repo
    else:
        w._album_data_repo = None
    w._all_items = []
    w._lib_ctrl = MagicMock()
    w._lib_ctrl.filtered_album_items.return_value = []
    w._album_detail_view = MagicMock()
    w._count = MagicMock()
    return w


class TestDetailIdentityResolution:

    def test_detail_uses_album_group_first(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        tracks = [_make_track(), _make_track()]
        group = _fake_group(tracks=tracks)
        cover_item = _fake_cover_item(album_group=group, tracks=tracks)
        w = _make_window_with_repo()
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        w._album_detail_view.set_album.assert_called()
        assert not ctrl._toast.called

    def test_detail_uses_album_key_from_album_data_repo(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        tracks = [_make_track(), _make_track()]
        group = _fake_group(title="RepoAlbum", album_key="k1", tracks=tracks)
        cover_item = _fake_cover_item(
            album_key="k1", title="ItemAlbum",
            album_group=None,
        )
        w = _make_window_with_repo(groups_dict={"k1": group})
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        w._album_detail_view.set_album.assert_called()
        assert not ctrl._toast.called

    def test_detail_uses_tracks_from_data(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        tracks = [_make_track(), _make_track()]
        cover_item = _fake_cover_item(
            album_key="orphan", title="Orphan",
            album_group=None, tracks=tracks,
        )
        w = _make_window_with_repo()
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        w._album_detail_view.set_album.assert_called()
        assert not ctrl._toast.called

    def test_detail_fallback_exact_match(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        item1 = _make_track(album="Exact Album", artist="Artist X", filepath="/a/1.flac")
        item2 = _make_track(album="Exact Album", artist="Artist X", filepath="/a/2.flac")
        cover_item = _fake_cover_item(
            album_key="", title="Exact Album", subtitle="Artist X",
            album_group=None, tracks=[],
        )
        w = _make_window_with_repo()
        w._all_items = [item1, item2]
        w._lib_ctrl.filtered_album_items.return_value = [item1, item2]
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        w._album_detail_view.set_album.assert_called()
        assert not ctrl._toast.called

    def test_detail_fallback_single_partial_match(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        item = _make_track(album="Great Album (Deluxe)", artist="Artist", filepath="/d/1.flac")
        cover_item = _fake_cover_item(
            album_key="", title="Album", subtitle="Artist",
            album_group=None, tracks=[],
        )
        w = _make_window_with_repo()
        w._all_items = [item]
        w._lib_ctrl.filtered_album_items.return_value = [item]
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        w._album_detail_view.set_album.assert_called()
        assert not ctrl._toast.called

    def test_detail_fallback_multiple_partial_matches_returns_without_opening(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        items = [
            _make_track(album="Great Album (Remaster)", artist="A", filepath="/r/1.flac"),
            _make_track(album="Great Album (Deluxe)", artist="B", filepath="/d/1.flac"),
        ]
        cover_item = _fake_cover_item(
            album_key="", title="Great Album", subtitle="",
            album_group=None, tracks=[],
        )
        w = _make_window_with_repo()
        w._all_items = items
        w._lib_ctrl.filtered_album_items.return_value = items
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        assert ctrl._toast.called
        w._count.setText.assert_called()
        w._album_detail_view.set_album.assert_not_called()

    def test_detail_does_not_open_remaster_when_ambiguous(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        items = [
            _make_track(album="Great Album (Remaster)", artist="Artist", filepath="/r/1.flac"),
            _make_track(album="Great Album (Deluxe)", artist="Artist", filepath="/d/1.flac"),
        ]
        cover_item = _fake_cover_item(
            album_key="", title="Great Album", subtitle="Artist",
            album_group=None, tracks=[],
        )
        w = _make_window_with_repo()
        w._all_items = items
        w._lib_ctrl.filtered_album_items.return_value = items
        ctrl = AlbumController(w)
        ctrl._toast = MagicMock()
        ctrl.show_album_detail_from_cover_item(cover_item)
        assert ctrl._toast.called
        w._count.setText.assert_called()
        w._album_detail_view.set_album.assert_not_called()
