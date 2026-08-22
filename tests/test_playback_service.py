"""Tests for PlaybackService — sole authority over PlaybackState."""

from pathlib import Path

import pytest

from michi.application.coordinator import PlaybackCoordinator
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
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.file_path == path
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

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
        assert playback_service.state.status != PlaybackStatus.PLAYING

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
        assert playback_service.state.status != PlaybackStatus.PLAYING
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
        assert playback_service.state.status != PlaybackStatus.PLAYING

    def test_pause_resume(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/tmp/test.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/test.mp3"))
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        playback_service.pause()
        # Commands express intent only: backend events carry the truth.
        assert playback_service.state.status == PlaybackStatus.PLAYING
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED
        playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PAUSED
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
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
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == second


class TestTruthfulPlaybackStatus:
    """TD-008B correction: LoadedMedia is acceptance, not playback start.

    PlaybackStatus.PLAYING/PAUSED/STOPPED must follow the backend
    playbackStateChanged signal; acceptance only commits track identity.
    """

    def test_accepted_is_not_playing(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.file_path == b
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_playing_state_commits_playing(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_no_playing_before_playing_state(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_paused_state_after_actually_playing(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED

    def test_stopped_state(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        fake_audio.trigger_playback_state(PlaybackStatus.STOPPED)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_stop_blocks_late_playing_state(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        playback_service.stop()
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_superseded_stale_lifecycle_ignored(self, playback_service, fake_audio):
        a = Path("/tmp/a.mp3")
        b = Path("/tmp/b.mp3")
        c = Path("/tmp/c.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        playback_service.load_and_play(b)
        playback_service.load_and_play(c)  # C supersedes B
        fake_audio.trigger_media_accepted(b)  # stale acceptance: ignored
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)  # stale B playing
        assert playback_service.state.file_path != b
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_media_accepted(c)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.file_path == c
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_runtime_rejection_after_acceptance_no_duplicate_notify(
        self, playback_service, fake_audio
    ):
        a = Path("/tmp/a.mp3")
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        playback_service.load_and_play(b)
        fake_audio.trigger_media_accepted(b)
        calls = []
        playback_service.subscribe_changed(lambda: calls.append(1))
        # errorOccurred + InvalidMedia for the same source fire twice:
        fake_audio.trigger_media_rejected(b, "decode failed")
        fake_audio.trigger_media_rejected(b, "decode failed")
        assert playback_service.state.file_path == b
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "decode failed"
        assert len(calls) == 1  # no duplicate notify


class TestCommandIntentAndLifecycleGuard:
    """Commands express intent only; PlaybackStatus follows backend events.

    play()/pause()/resume() must never mutate status or notify. PLAYING is
    published only when the backend emits it AND the current candidate was
    accepted. stop() blocks late active-state events (PLAYING and PAUSED).
    """

    def _play_a(self, playback_service, fake_audio):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        return a

    def test_play_command_does_not_claim_playing(self, playback_service, fake_audio):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED
        playback_service.play()
        assert playback_service.state.status == PlaybackStatus.STOPPED
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_resume_command_does_not_claim_playing(self, playback_service, fake_audio):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED
        playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PAUSED
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_pause_command_does_not_claim_paused(self, playback_service, fake_audio):
        self._play_a(playback_service, fake_audio)
        playback_service.pause()
        assert playback_service.state.status == PlaybackStatus.PLAYING
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED

    def test_late_playing_event_after_stop_ignored(self, playback_service, fake_audio):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_late_paused_event_after_stop_ignored(self, playback_service, fake_audio):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_playing_event_before_acceptance_blocked(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        playback_service.load_and_play(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_reentrant_playing_event_during_load_blocked(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        b = Path("/tmp/b.mp3")

        def reentrant_load(p):
            fake_audio.loaded = p
            fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)

        monkeypatch.setattr(fake_audio, "load", reentrant_load)
        playback_service.load_and_play(b)
        # B remains pending and uncommitted; no false PLAYING claim survives.
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.file_path == b
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_play_command_failure_preserves_state(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)

        def failing_play():
            raise RuntimeError("play failed")

        monkeypatch.setattr(fake_audio, "play", failing_play)
        with pytest.raises(RuntimeError, match="play failed"):
            playback_service.play()
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_resume_command_failure_preserves_state(
        self, playback_service, fake_audio, monkeypatch
    ):
        a = Path("/tmp/a.mp3")
        playback_service.load_and_play(a)
        fake_audio.trigger_media_accepted(a)
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)

        def failing_resume():
            raise RuntimeError("resume failed")

        monkeypatch.setattr(fake_audio, "resume", failing_resume)
        with pytest.raises(RuntimeError, match="resume failed"):
            playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PAUSED

    def test_load_failure_restores_intent_and_acceptance(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)

        def failing_load(p):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)
        with pytest.raises(RuntimeError, match="load failed"):
            playback_service.load_and_play(Path("/tmp/b.mp3"))
        # Pending cleared: late acceptance for B must not commit.
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        # Previous intent/acceptance restored: A's lifecycle still applies.
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED

    def test_play_failure_inside_load_and_play_restores_state(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)

        def failing_play():
            raise RuntimeError("play failed")

        monkeypatch.setattr(fake_audio, "play", failing_play)
        with pytest.raises(RuntimeError, match="play failed"):
            playback_service.load_and_play(Path("/tmp/b.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.PLAYING
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.PAUSED

    def test_play_failure_from_false_intent_blocks_late_playing(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED

        def failing_play():
            raise RuntimeError("play failed")

        monkeypatch.setattr(fake_audio, "play", failing_play)
        with pytest.raises(RuntimeError, match="play failed"):
            playback_service.play()
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_resume_failure_from_false_intent_blocks_late_playing(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED

        def failing_resume():
            raise RuntimeError("resume failed")

        monkeypatch.setattr(fake_audio, "resume", failing_resume)
        with pytest.raises(RuntimeError, match="resume failed"):
            playback_service.resume()
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_play_failure_from_false_intent_blocks_late_paused(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED

        def failing_play():
            raise RuntimeError("play failed")

        monkeypatch.setattr(fake_audio, "play", failing_play)
        with pytest.raises(RuntimeError, match="play failed"):
            playback_service.play()
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_successful_play_still_arms_intent_for_reentrant_playing(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED

        def reentrant_play():
            fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)

        monkeypatch.setattr(fake_audio, "play", reentrant_play)
        playback_service.play()
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_successful_resume_still_arms_intent_for_reentrant_playing(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._play_a(playback_service, fake_audio)
        playback_service.stop()
        assert playback_service.state.status == PlaybackStatus.STOPPED

        def reentrant_resume():
            fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)

        monkeypatch.setattr(fake_audio, "resume", reentrant_resume)
        playback_service.resume()
        assert playback_service.state.status == PlaybackStatus.PLAYING

    def test_duplicate_lifecycle_events_notify_once(self, playback_service, fake_audio):
        self._play_a(playback_service, fake_audio)
        calls = []
        playback_service.subscribe_changed(lambda: calls.append(1))
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        fake_audio.trigger_playback_state(PlaybackStatus.PAUSED)
        fake_audio.trigger_playback_state(PlaybackStatus.STOPPED)
        fake_audio.trigger_playback_state(PlaybackStatus.STOPPED)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert len(calls) == 3
        assert playback_service.state.status == PlaybackStatus.PLAYING


class TestRejectionCallback:
    """TD-015: async rejection notifies exactly once via an optional callback.

    The callback is captured and cleared before invocation; acceptance never
    invokes it; sync failures, stop(), and supersession clear it silently.
    """

    def test_rejection_invokes_callback_exactly_once(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        rejected = []
        playback_service.load_and_play(
            b, on_rejected=lambda p, m: rejected.append((p, m))
        )
        fake_audio.trigger_media_rejected(b, "bad media")
        fake_audio.trigger_media_rejected(b, "bad media")  # duplicate signal
        assert rejected == [(b, "bad media")]
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "bad media"

    def test_acceptance_does_not_invoke_rejection_callback(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        accepted = []
        rejected = []
        playback_service.load_and_play(
            b,
            on_accepted=lambda p: accepted.append(p),
            on_rejected=lambda p, m: rejected.append(m),
        )
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_media_accepted(b)  # duplicate: nothing further
        assert accepted == [b]
        assert rejected == []

    def test_sync_failure_clears_rejection_callback_without_invoking(
        self, playback_service, fake_audio, monkeypatch
    ):
        b = Path("/tmp/b.mp3")
        rejected = []

        def failing_load(p):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)
        with pytest.raises(RuntimeError, match="load failed"):
            playback_service.load_and_play(
                b, on_rejected=lambda p, m: rejected.append(m)
            )
        assert rejected == []
        # Slot cleared: a late rejection must not invoke it.
        fake_audio.trigger_media_rejected(b, "late")
        assert rejected == []

    def test_stop_clears_rejection_callback_without_invoking(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        rejected = []
        playback_service.load_and_play(b, on_rejected=lambda p, m: rejected.append(m))
        playback_service.stop()
        fake_audio.trigger_media_rejected(b, "late")
        assert rejected == []

    def test_superseded_candidate_rejection_invokes_no_stale_callback(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        c = Path("/tmp/c.mp3")
        rejected_b = []
        rejected_c = []
        playback_service.load_and_play(b, on_rejected=lambda p, m: rejected_b.append(m))
        playback_service.load_and_play(c, on_rejected=lambda p, m: rejected_c.append(m))
        fake_audio.trigger_media_rejected(b, "stale")  # B superseded
        assert rejected_b == []
        assert rejected_c == []
        fake_audio.trigger_media_rejected(c, "real")
        assert rejected_b == []
        assert rejected_c == ["real"]


class TestPrepareForResume:
    """M5.C4: prepare_for_resume — startup resume path (load + seek, NO autoplay).

    prepare_for_resume requests the backend LOAD of a candidate for session
    resume and, only on acceptance, seeks the backend to the persisted
    position. It NEVER calls play() and never arms intent: status stays
    STOPPED until the user's later play() starts playback from the sought
    position.
    """

    def test_prepare_loads_but_does_not_play(
        self, playback_service, fake_audio, monkeypatch
    ):
        b = Path("/tmp/b.mp3")
        play_calls = []
        monkeypatch.setattr(fake_audio, "play", lambda: play_calls.append(1))
        playback_service.prepare_for_resume(b, 222000)
        assert fake_audio.loaded == b
        assert play_calls == []  # prepare NEVER autoplays
        assert fake_audio.state != "playing"

    def test_prepare_commits_only_after_acceptance(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        assert playback_service.state.file_path is None  # not committed yet
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.file_path == b
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_prepare_stays_stopped_after_acceptance(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        calls = []
        playback_service.subscribe_changed(lambda: calls.append(1))
        playback_service.prepare_for_resume(b, 222000)
        assert len(calls) == 1  # request registered as pending
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.status == PlaybackStatus.STOPPED  # NOT PLAYING
        assert len(calls) == 2  # acceptance notified exactly once

    def test_prepare_seek_after_acceptance(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        assert fake_audio.seek_calls == []  # nothing sought yet
        fake_audio.trigger_media_accepted(b)
        # exactly one seek, and only AFTER the acceptance committed the track
        assert fake_audio.seek_calls == [222000]

    def test_prepare_negative_position_clamped(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, -5)
        fake_audio.trigger_media_accepted(b)
        assert fake_audio.seek_calls == [0]

    def test_prepare_rejection_safe(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_rejected(b, "gone")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path is None  # never committed
        assert playback_service.state.error_message == "gone"
        # Pending cleared: a late acceptance of B does nothing.
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.file_path is None
        assert fake_audio.seek_calls == []

    def test_prepare_stop_cancels(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        playback_service.stop()
        fake_audio.trigger_media_accepted(b)  # late acceptance after cancel
        assert playback_service.state.file_path is None
        assert fake_audio.seek_calls == []

    def test_prepare_supersession_protects_new_request(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        c = Path("/tmp/c.mp3")
        playback_service.prepare_for_resume(b, 222000)
        playback_service.load_and_play(c)  # user selects C; C supersedes B
        fake_audio.trigger_media_accepted(b)  # stale B acceptance: dropped
        assert playback_service.state.file_path is None
        assert fake_audio.seek_calls == []  # stale B never seeks
        fake_audio.trigger_media_accepted(c)
        assert playback_service.state.file_path == c
        assert fake_audio.seek_calls == []  # C is a play request, not a resume

    def test_prepare_then_user_play_resumes(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_accepted(b)
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert fake_audio.position() == 222000  # backend sought after acceptance
        playback_service.play()
        assert fake_audio.state == "playing"
        assert playback_service.state.status == PlaybackStatus.STOPPED  # intent only
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING  # resumed

    def test_prepare_late_playing_state_ignored(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_accepted(b)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)  # no user play()
        assert playback_service.state.status == PlaybackStatus.STOPPED  # intent guard


class TestResumePreparedEvent:
    """M5-LAST-GATE-2 — the minimal public resume-prepared event.

    ``subscribe_resume_prepared(cb: Callable[[Path, int], None])`` /
    ``unsubscribe_resume_prepared(cb)`` fires ONCE when a prepare_for_resume
    reaches media accepted + backend position update post-seek, carrying the
    committed file_path and the CONFIRMED position. It never autoplays, is
    not fired for normal load_and_play, is not fired again after release, and
    position 0 fires correctly. Media acceptance ALONE must not fire it — the
    backend position confirmation is the release signal.
    """

    def test_resume_prepared_fires_after_position_update(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_accepted(b)
        assert events == []  # WAITING_POSITION: acceptance alone is no release
        playback_service.update_position(222000)  # backend position confirms
        assert events == [(b, 222000)]  # fired ONCE with the confirmed position
        playback_service.update_position(223000)  # further updates: no replay
        assert events == [(b, 222000)]

    def test_resume_prepared_fires_for_position_zero(
        self, playback_service, fake_audio
    ):
        b = Path("/tmp/b.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        playback_service.prepare_for_resume(b, 0)
        fake_audio.trigger_media_accepted(b)
        playback_service.update_position(0)  # position 0 is a valid confirmation
        assert events == [(b, 0)]

    def test_resume_prepared_not_fired_for_load_and_play(
        self, playback_service, fake_audio
    ):
        c = Path("/tmp/c.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        playback_service.load_and_play(c)
        fake_audio.trigger_media_accepted(c)
        playback_service.update_position(5000)
        assert events == []  # normal playback is never a resume

    def test_resume_prepared_superseded_no_fire(self, playback_service, fake_audio):
        b = Path("/tmp/b.mp3")
        c = Path("/tmp/c.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        playback_service.prepare_for_resume(b, 222000)
        playback_service.load_and_play(c)  # C supersedes B's prepare
        fake_audio.trigger_media_accepted(c)
        playback_service.update_position(222000)
        assert events == []  # a superseded resume never fires


class TestReentrantSeek:
    """M5-PRODUCTION-LIFECYCLE-GATE — REENTRANT SEEK (§29-D/E, §10).

    A Qt backend can emit positionChanged SYNCHRONOUSLY from within seek()
    (the seek primitive). ``_apply_prepare_seek`` must arm the
    ``_resume_prepared_pending`` latch BEFORE issuing the backend seek, so a
    synchronous position callback DURING seek() fires resume_prepared exactly
    once — never lost to a latch armed after the fact, never double-fired
    (the latch disarms on the first fire). A seek that RAISES must disarm the
    latch cleanly: no false resume-complete, no eternal latch, and the
    acceptance path must contain the failure (no crash escaping into the
    backend callback).

    The audio path is the production wiring: the PlaybackCoordinator forwards
    the fake's position_changed channel into PlaybackService.update_position
    (trigger_position alone has no subscribers without the coordinator).
    """

    def _wire_audio_path(self, playback_service, fake_audio, queue_service):
        coordinator = PlaybackCoordinator(fake_audio, queue_service, playback_service)
        coordinator.start()
        return coordinator

    def test_reentrant_seek_position_callback_not_lost(
        self, playback_service, fake_audio, queue_service, monkeypatch
    ):
        b = Path("/tmp/b.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        self._wire_audio_path(playback_service, fake_audio, queue_service)

        # The backend emits positionChanged synchronously DURING seek().
        def reentrant_seek(ms):
            fake_audio.seek_calls.append(ms)
            fake_audio.trigger_position(ms)

        monkeypatch.setattr(fake_audio, "seek", reentrant_seek)
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_accepted(b)

        # The synchronous callback during seek() confirmed the resume: exactly
        # ONE event with the committed path and the confirmed position.
        assert events == [(b, 222000)]  # RED: latch armed AFTER seek -> lost
        assert fake_audio.seek_calls == [222000]
        assert playback_service.state.file_path == b
        assert playback_service.state.position_ms == 222000
        assert playback_service.state.status is PlaybackStatus.STOPPED
        assert fake_audio.state != "playing"  # never autoplays

    def test_reentrant_seek_no_double_fire(
        self, playback_service, fake_audio, queue_service, monkeypatch
    ):
        b = Path("/tmp/b.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        self._wire_audio_path(playback_service, fake_audio, queue_service)

        def reentrant_seek(ms):
            fake_audio.seek_calls.append(ms)
            fake_audio.trigger_position(ms)

        monkeypatch.setattr(fake_audio, "seek", reentrant_seek)
        playback_service.prepare_for_resume(b, 222000)
        fake_audio.trigger_media_accepted(b)
        assert events == [(b, 222000)]  # the reentrant fire (exactly once)

        # The latch is DISARMED by the reentrant fire: a LATER position update
        # must not emit a second resume_prepared.
        playback_service.update_position(230000)
        assert events == [(b, 222000)]  # RED: current code fires (b, 230000)

    def test_seek_failure_disarms_cleanly(
        self, playback_service, fake_audio, queue_service, monkeypatch
    ):
        b = Path("/tmp/b.mp3")
        events = []
        playback_service.subscribe_resume_prepared(
            lambda p, pos: events.append((p, pos))
        )
        self._wire_audio_path(playback_service, fake_audio, queue_service)

        def failing_seek(ms):
            fake_audio.seek_calls.append(ms)
            raise RuntimeError("seek failed")

        monkeypatch.setattr(fake_audio, "seek", failing_seek)
        playback_service.prepare_for_resume(b, 222000)

        # The acceptance path CONTAINS the seek failure: no crash escapes into
        # the backend callback; the error surfaces on the state; the latch is
        # disarmed; no false resume-complete is emitted.
        fake_audio.trigger_media_accepted(b)  # RED: current code raises here
        assert fake_audio.seek_calls == [222000]
        assert playback_service.state.file_path == b  # acceptance committed B
        assert playback_service.state.status is PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "seek failed"
        assert events == []  # no false resume-complete

        # No eternal latch: a later position update must NOT emit the event.
        playback_service.update_position(230000)
        assert events == []


class TestLoadDisposition:
    """M11.3C-R6.1: la disposición de la fuente previa es explícita y
    PlaybackService nunca infiere aceptación tras un fallo destructivo."""

    def _accept_a(self, playback_service, fake_audio):
        playback_service.load_and_play(Path("/m/a.flac"))
        fake_audio.trigger_media_accepted(Path("/m/a.flac"))
        assert playback_service._accepted is True

    def test_audio_load_error_data_contract(self):
        from michi.application.ports import AudioLoadError

        err = AudioLoadError(Path("/m/b.flac"), "boom", previous_source_preserved=False)
        assert str(err) == "boom"
        assert err.candidate_path == Path("/m/b.flac")
        assert err.detail == "boom"
        assert err.previous_source_preserved is False

    def test_destructive_failure_does_not_restore_acceptance(
        self, playback_service, fake_audio, monkeypatch
    ):
        from michi.application.ports import AudioLoadError

        self._accept_a(playback_service, fake_audio)
        monkeypatch.setattr(
            fake_audio,
            "load",
            lambda p: (_ for _ in ()).throw(
                AudioLoadError(
                    Path("/m/b.flac"), "arm B failed", previous_source_preserved=False
                )
            ),
        )
        with pytest.raises(AudioLoadError):
            playback_service.load_and_play(Path("/m/b.flac"))
        assert playback_service.state.file_path == Path("/m/a.flac")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service._accepted is False
        assert playback_service._intent is False
        assert playback_service._pending_path is None

    def test_play_reloads_committed_track_after_destructive_failure(
        self, playback_service, fake_audio, monkeypatch
    ):
        from michi.application.ports import AudioLoadError

        self._accept_a(playback_service, fake_audio)
        load_calls = []

        def failing_load(p):
            load_calls.append(p)
            raise AudioLoadError(
                Path("/m/b.flac"), "arm B failed", previous_source_preserved=False
            )

        monkeypatch.setattr(fake_audio, "load", failing_load)
        with pytest.raises(AudioLoadError):
            playback_service.load_and_play(Path("/m/b.flac"))
        # play() recarga A por el camino canónico (load + play, sin no-op)
        monkeypatch.setattr(fake_audio, "load", lambda p: load_calls.append(p))
        playback_service.play()
        assert load_calls[-1] == Path("/m/a.flac")
        fake_audio.trigger_media_accepted(Path("/m/a.flac"))
        assert playback_service._accepted is True
        assert playback_service.state.file_path == Path("/m/a.flac")

    def test_preserved_failure_restores_acceptance(
        self, playback_service, fake_audio, monkeypatch
    ):
        from michi.application.ports import AudioLoadError

        self._accept_a(playback_service, fake_audio)
        monkeypatch.setattr(
            fake_audio,
            "load",
            lambda p: (_ for _ in ()).throw(
                AudioLoadError(
                    Path("/m/b.flac"),
                    "pre-commit failure",
                    previous_source_preserved=True,
                )
            ),
        )
        with pytest.raises(AudioLoadError):
            playback_service.load_and_play(Path("/m/b.flac"))
        # aceptación e intención previas restauradas (no destructivo)
        assert playback_service._accepted is True
        assert playback_service._intent is True

    def test_legacy_generic_exception_restores_acceptance(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._accept_a(playback_service, fake_audio)
        monkeypatch.setattr(
            fake_audio,
            "load",
            lambda p: (_ for _ in ()).throw(RuntimeError("load failed")),
        )
        with pytest.raises(RuntimeError):
            playback_service.load_and_play(Path("/m/b.flac"))
        assert playback_service._accepted is True  # comportamiento legacy
        assert playback_service._intent is True

    def test_play_no_reload_when_accepted(
        self, playback_service, fake_audio, monkeypatch
    ):
        self._accept_a(playback_service, fake_audio)
        load_calls = []
        monkeypatch.setattr(fake_audio, "load", lambda p: load_calls.append(p))
        playback_service.play()
        # sin reload: play() directo sobre la fuente aceptada (R6 stop→play)
        assert load_calls == []

    def test_play_no_reload_while_pending(
        self, playback_service, fake_audio, monkeypatch
    ):
        from michi.application.ports import AudioLoadError

        self._accept_a(playback_service, fake_audio)
        monkeypatch.setattr(
            fake_audio,
            "load",
            lambda p: (_ for _ in ()).throw(
                AudioLoadError(
                    Path("/m/b.flac"), "arm B failed", previous_source_preserved=False
                )
            ),
        )
        with pytest.raises(AudioLoadError):
            playback_service.load_and_play(Path("/m/b.flac"))
        # candidato pendiente nuevo → play() no recarga el track lógico
        monkeypatch.setattr(
            fake_audio, "load", lambda p: setattr(fake_audio, "loaded", p)
        )
        playback_service.load_and_play(Path("/m/c.flac"))
        playback_service.play()
        assert fake_audio.loaded == Path("/m/c.flac")  # sin recarga de A

    def test_prepare_for_resume_destructive_failure(
        self, playback_service, fake_audio, monkeypatch
    ):
        from michi.application.ports import AudioLoadError

        self._accept_a(playback_service, fake_audio)
        monkeypatch.setattr(
            fake_audio,
            "load",
            lambda p: (_ for _ in ()).throw(
                AudioLoadError(
                    Path("/m/b.flac"), "arm B failed", previous_source_preserved=False
                )
            ),
        )
        with pytest.raises(AudioLoadError):
            playback_service.prepare_for_resume(Path("/m/b.flac"), 120000)
        assert playback_service._accepted is False
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.file_path == Path("/m/a.flac")
        assert playback_service._pending_path is None
        assert playback_service._resume_prepared_pending is False
