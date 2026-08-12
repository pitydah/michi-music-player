"""Tests for PlaybackService — sole authority over PlaybackState."""

from pathlib import Path

import pytest

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

    def test_load_and_play_requires_acceptance(self, playback_service, fake_audio):
        path = Path("/tmp/test.mp3")
        playback_service.load_and_play(path)
        assert fake_audio.loaded == path
        assert fake_audio.state == "playing"
        # Candidate requested but not yet accepted: no false PLAYING claim.
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path is None
        fake_audio.trigger_media_accepted(path)
        assert playback_service.state.status == PlaybackStatus.PLAYING
        assert playback_service.state.file_path == path

    def test_acceptance_commits_state_exactly_once(self, playback_service, fake_audio):
        calls = []

        def cb():
            calls.append(1)

        playback_service.subscribe_changed(cb)
        path = Path("/tmp/b.mp3")
        playback_service.load_and_play(path)
        assert len(calls) == 1  # request registered as pending
        fake_audio.trigger_media_accepted(path)
        assert len(calls) == 2  # acceptance committed
        fake_audio.trigger_media_accepted(path)  # duplicate signal
        assert len(calls) == 2  # no duplicate commit
        assert playback_service.state.file_path == path
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_rejection_keeps_last_committed_file_and_sets_error(
        self, playback_service, fake_audio
    ):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        playback_service.load_and_play(Path("/tmp/b.mp3"))
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "unsupported format")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == a
        assert playback_service.state.error_message == "unsupported format"

    def test_unknown_acceptance_ignored(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(Path("/tmp/other.mp3"))
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path is None
        # Pending candidate survives an unrelated acceptance.
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.status == PlaybackStatus.PLAYING
        assert playback_service.state.file_path == b

    def test_unknown_rejection_ignored(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/tmp/b.mp3"))
        fake_audio.trigger_media_rejected(Path("/tmp/other.mp3"), "boom")
        assert playback_service.state.error_message is None
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_runtime_error_on_committed_track_surfaces(
        self, playback_service, fake_audio
    ):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        fake_audio.trigger_media_rejected(a, "decode failed")
        assert playback_service.state.error_message == "decode failed"
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == a

    def test_stop_invalidates_pending_candidate(self, playback_service, fake_audio):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        playback_service.load_and_play(Path("/tmp/b.mp3"))
        playback_service.stop()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == a

    def test_sync_failure_clears_pending_and_propagates(
        self, playback_service, fake_audio, monkeypatch
    ):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)

        def failing_load(p):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)

        with pytest.raises(RuntimeError, match="load failed"):
            playback_service.load_and_play(Path("/tmp/b.mp3"))

        # Pending was cleared: a late acceptance must not resurrect the candidate.
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert playback_service.state.file_path == a
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_pause_resume(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/tmp/test.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/test.mp3"))
        playback_service.pause()
        assert playback_service.state.status == PlaybackStatus.PAUSED
        playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_stop(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/tmp/test.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/test.mp3"))
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
        first = Path("/tmp/first.mp3")
        second = Path("/tmp/second.mp3")
        playback_service.load_and_play(first)
        fake_audio.trigger_media_accepted(first)
        playback_service.switch_track(second)
        assert fake_audio.loaded == second
        # Not accepted yet: honest STOPPED + last committed file.
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == first
        fake_audio.trigger_media_accepted(second)
        assert playback_service.state.status == PlaybackStatus.PLAYING
        assert playback_service.state.file_path == second
