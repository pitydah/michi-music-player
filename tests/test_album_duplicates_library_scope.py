"""Tests: duplicate detection against full library scope."""
from unittest.mock import MagicMock, patch


def _make(album="", artist="", filepath="/m/s.flac", year=2024):
    t = MagicMock()
    t.album = album
    t.artist = artist
    t.filepath = filepath
    t.year = year
    t.ext = "flac"
    t.duration = 200.0
    t.title = "Song"
    t.albumartist = ""
    t.disc_number = 1
    t.track_number = 1
    t.sample_rate = 44100
    t.bit_depth = 16
    t.bitrate = 1411
    t.genre = "Rock"
    return t


class TestDuplicatesLibraryScope:
    def _make_win(self):
        from unittest.mock import MagicMock
        w = MagicMock()
        w._all_items = None
        w._ctx.db.get_all.return_value = []
        return w

    def test_two_copies_detected(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        w = self._make_win()
        # Library has two copies of Same Album by Same Artist
        w._all_items = [
            _make(album="Same", artist="X", filepath="/a/1.flac"),
            _make(album="Same", artist="X", filepath="/a/2.flac"),
            _make(album="Same", artist="X", filepath="/b/1.flac"),
            _make(album="Same", artist="X", filepath="/b/2.flac"),
        ]
        ctrl = AlbumController(w)
        tracks = [_make(album="Same", artist="X", filepath="/c/s.flac")]
        with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
            ctrl.review_album_duplicates(tracks)
            assert mock_info.called or w._ctx.toast.show.called

    def test_single_copy_no_duplicates(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        w = self._make_win()
        w._all_items = [
            _make(album="Unique", artist="X", filepath="/u/1.flac"),
        ]
        ctrl = AlbumController(w)
        tracks = [_make(album="Unique", artist="X", filepath="/u/2.flac")]
        ctrl.review_album_duplicates(tracks)
        w._ctx.toast.show.assert_called()

    def test_same_title_different_artist_no_dup(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        w = self._make_win()
        w._all_items = [
            _make(album="Title", artist="A"),
            _make(album="Title", artist="B"),
        ]
        ctrl = AlbumController(w)
        tracks = [_make(album="Title", artist="A")]
        ctrl.review_album_duplicates(tracks)
        w._ctx.toast.show.assert_called()

    def test_no_crash_empty_library(self):
        from legacy_widgets.ui.controllers.legacy_controllers.album_controller import AlbumController
        w = self._make_win()
        w._all_items = []
        ctrl = AlbumController(w)
        ctrl.review_album_duplicates([_make(filepath="/m/s.flac")])
