"""Tests for PlaybackController."""
from sources.base_source import TrackRef
from core.playback_controller import PlaybackController


class TestPlaybackController:
    def test_play_trackref_local(self, mock_window):
        ctrl = PlaybackController(mock_window)
        track = TrackRef(uri="/tmp/test.flac", title="Test Song", artist="Test Artist",
                         album="Test Album", duration=180.0)
        ctrl.play_trackref(track)
        mock_window._playback.enqueue.assert_called_once()
        mock_window._player_bar_ctrl.set_track_from_ref.assert_called_once()
        mock_window._ctx.notify_track.assert_called_once()

    def test_play_trackref_http(self, mock_window):
        ctrl = PlaybackController(mock_window)
        track = TrackRef(uri="http://example.com/stream", title="Radio",
                         artist="Station", duration=0)
        ctrl.play_trackref(track)
        mock_window._playback.play_url.assert_called_once()

    def test_play_file(self, mock_window):
        ctrl = PlaybackController(mock_window)
        ctrl.play_file("/tmp/test.flac")
        mock_window._playback.enqueue.assert_called_once()

    def test_on_state_playing(self, mock_window):
        from audio.player import PlaybackState
        ctrl = PlaybackController(mock_window)
        ctrl.on_state(PlaybackState.PLAYING)
        mock_window._player_bar_ctrl.set_state.assert_called_with("playing")

    def test_on_state_stopped(self, mock_window):
        from audio.player import PlaybackState
        ctrl = PlaybackController(mock_window)
        ctrl.on_state(PlaybackState.STOPPED)
        mock_window._player_bar_ctrl.set_state.assert_called_with("stopped")
        mock_window._player_bar_ctrl.set_position.assert_called_with(0)

    def test_on_stop(self, mock_window):
        ctrl = PlaybackController(mock_window)
        ctrl.on_stop()
        mock_window._playback.stop.assert_called_once()
        mock_window._player_bar_ctrl.reset.assert_called_once()
        mock_window._bg_theme.reset.assert_called_once()
