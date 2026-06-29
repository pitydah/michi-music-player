"""Tests: playback context — play_trackref, NOW_PLAYING_UPDATED, selection."""

from unittest.mock import MagicMock


class TestPlaybackContextEvents:

    def test_play_trackreg_calls_update_selection(self):
        ctx = MagicMock()
        window = MagicMock()
        window._ctx.context_svc = ctx
        window._ctx.items_index = {}

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(window)

        track = MagicMock()
        track.uri = "/music/song.flac"
        track.title = "Song"
        track.artist = "Artist"
        track.album = "Album"
        track.genre = "Rock"
        track.duration = 240

        ctrl.play_trackref(track)

        ctx.update_selection.assert_called_once()
        args = ctx.update_selection.call_args
        kwargs = args[1]
        assert kwargs.get("scope") == "track"
        assert kwargs.get("album") == "Album"
        assert kwargs.get("artist") == "Artist"

    def test_play_trackreg_calls_record_now_playing(self):
        ctx = MagicMock()
        window = MagicMock()
        window._ctx.context_svc = ctx
        window._ctx.items_index = {}

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(window)

        track = MagicMock()
        track.uri = "/music/song.flac"
        track.title = "Song"
        track.artist = "Artist"
        track.album = "Album"
        track.duration = 0

        ctrl.play_trackref(track)
        ctx.record_now_playing_updated.assert_called_once_with("Song", "Artist", "Album")
