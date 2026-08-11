"""Tests for PlaybackService — sole authority over PlaybackState."""

from pathlib import Path

from michi.domain.playback import PlaybackStatus


class TestPlaybackService:
    def test_initial_state(self, playback_service):
        s = playback_service.state
        assert s.status == PlaybackStatus.STOPPED
        assert s.file_path is None
        assert s.position_ms == 0
        assert s.duration_ms == 0
        assert s.volume == 100
        assert s.muted is False

    def test_load_and_play(self, playback_service, fake_audio):
        path = Path("/tmp/test.mp3")
        playback_service.load_and_play(path)
        assert fake_audio.loaded == path
        assert fake_audio.state == "playing"
        assert playback_service.state.status == PlaybackStatus.PLAYING
        assert playback_service.state.file_path == path

    def test_pause_resume(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/tmp/test.mp3"))
        playback_service.pause()
        assert playback_service.state.status == PlaybackStatus.PAUSED
        playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_stop(self, playback_service):
        playback_service.load_and_play(Path("/tmp/test.mp3"))
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.position_ms == 0

    def test_seek(self, playback_service):
        playback_service.seek(30000)
        assert playback_service.state.position_ms == 30000

    def test_volume_clamping(self, playback_service, fake_audio):
        playback_service.set_volume(150)
        assert playback_service.state.volume == 100
        assert fake_audio.volume == 100
        playback_service.set_volume(-5)
        assert playback_service.state.volume == 0
        assert fake_audio.volume == 0

    def test_mute(self, playback_service, fake_audio):
        playback_service.set_muted(True)
        assert playback_service.state.muted is True
        assert fake_audio.muted is True

    def test_update_position_and_duration(self, playback_service):
        playback_service.update_position(5000)
        assert playback_service.state.position_ms == 5000
        playback_service.update_duration(200000)
        assert playback_service.state.duration_ms == 200000

    def test_restore_volume(self, playback_service, fake_audio):
        playback_service.restore_volume(42, True)
        assert playback_service.state.volume == 42
        assert playback_service.state.muted is True
        assert fake_audio.volume == 42
        assert fake_audio.muted is True

    def test_switch_track(self, playback_service, fake_audio):
        path = Path("/tmp/second.mp3")
        playback_service.load_and_play(Path("/tmp/first.mp3"))
        playback_service.switch_track(path)
        assert fake_audio.loaded == path
        assert playback_service.state.status == PlaybackStatus.PLAYING
        assert playback_service.state.file_path == path
