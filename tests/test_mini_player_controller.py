"""Tests for MiniPlayerController."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def win():
    w = MagicMock()
    w._ctx = MagicMock()
    w._ctx.playback = MagicMock()
    w._ctx.mini_player = None
    w._ctx.items_index = {}
    return w


@pytest.fixture
def ctrl(win):
    from legacy_widgets.ui.controllers.legacy_controllers.mini_player_controller import MiniPlayerController
    c = MiniPlayerController.__new__(MiniPlayerController)
    from PySide6.QtCore import QObject
    QObject.__init__(c)
    c._win = win
    c._ctx = win._ctx
    c._svc = None
    return c


class TestMiniPlayerController:
    def test_init_sets_win_ctx(self, ctrl, win):
        assert ctrl._win is win
        assert ctrl._ctx is win._ctx

    def test_open_creates_mini_player_when_none(self, ctrl, win):
        with (patch("ui.mini_player.MiniPlayer") as mock_mp_cls,
              patch("audio.player.PlaybackState")):
            mock_mp = mock_mp_cls.return_value
            ctrl.open()
            mock_mp_cls.assert_called_once_with(win._ctx.playback, win)
            assert win._ctx.mini_player is mock_mp
            mock_mp.show.assert_called_once()
            mock_mp.raise_.assert_called_once()
            mock_mp.activateWindow.assert_called_once()
            mock_mp.play_clicked.connect.assert_called()
            mock_mp.prev_clicked.connect.assert_called()
            mock_mp.next_clicked.connect.assert_called()
            mock_mp.seek_requested.connect.assert_called()

    def test_open_uses_existing_mini_player(self, ctrl, win):
        existing = MagicMock()
        win._ctx.mini_player = existing
        with (patch("ui.mini_player.MiniPlayer") as mock_mp_cls,
              patch("audio.player.PlaybackState")):
            ctrl.open()
            mock_mp_cls.assert_not_called()
            existing.show.assert_called_once()

    def test_open_emits_signal(self, ctrl):
        with (patch("ui.mini_player.MiniPlayer"),
              patch("audio.player.PlaybackState")):
            results = []
            ctrl.mini_player_opened.connect(lambda: results.append(True))
            ctrl.open()
            assert results == [True]

    def test_close_hides_mini_player(self, ctrl, win):
        mp = MagicMock()
        win._ctx.mini_player = mp
        ctrl.close()
        mp.hide.assert_called_once()

    def test_close_does_nothing_when_none(self, ctrl):
        ctrl.close()

    def test_close_emits_signal(self, ctrl, win):
        mp = MagicMock()
        win._ctx.mini_player = mp
        results = []
        ctrl.mini_player_closed.connect(lambda: results.append(True))
        ctrl.close()
        assert results == [True]

    def test_update_metadata_with_current(self, ctrl, win):
        mp = MagicMock()
        win._ctx.playback.current = "/path/to/song.flac"
        with (patch("library.cover_art_service.CoverArtService") as mock_cas,
              patch("ui.controllers.mini_player_controller.os.path.basename",
                    return_value="song.flac")):
            mock_cas.quality_label.return_value = ("FLAC 44.1kHz", 0)
            mock_cas.find_cover.return_value = "/path/to/cover.jpg"
            ctrl._update_metadata(mp)
            mp.set_track.assert_called()

    def test_update_metadata_with_item(self, ctrl, win):
        mp = MagicMock()
        win._ctx.playback.current = "/path/to/song.flac"
        item = MagicMock()
        item.artist = "Artist"
        item.title = "Title"
        win._ctx.items_index = {"/path/to/song.flac": item}
        with (patch("library.cover_art_service.CoverArtService") as mock_cas,
              patch("ui.controllers.mini_player_controller.os.path.basename",
                    return_value="song.flac")):
            mock_cas.quality_label.return_value = ("FLAC", 0)
            mock_cas.find_cover.return_value = "/path/to/cover.jpg"
            ctrl._update_metadata(mp)
            mp.set_track.assert_called_with("Title", "Artist", "/path/to/cover.jpg")

    def test_update_metadata_no_current(self, ctrl, win):
        mp = MagicMock()
        win._ctx.playback.current = None
        with patch("library.cover_art_service.CoverArtService"):
            ctrl._update_metadata(mp)
            mp.set_track.assert_called_with("Sin reproducción", "", "")
