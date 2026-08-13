"""Tests for QueueService — sole authority over QueueState."""

from pathlib import Path

import pytest

from michi.domain.playback import PlaybackStatus


class TestQueueService:
    def test_empty_state(self, queue_service):
        assert queue_service.state.count == 0
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None

    def test_add_track(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        assert queue_service.state.count == 1

    def test_play_index(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(1)
        # Not committed before acceptance.
        assert queue_service.state.current_index == -1
        assert fake_audio.state == "playing"
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_next(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.next()
        assert queue_service.state.current_index == 0  # pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_next_at_end(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.next()
        assert queue_service.state.current_index == 0  # stays

    def test_previous(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        queue_service.previous()
        assert queue_service.state.current_index == 1  # pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

    def test_previous_at_start(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.previous()
        assert queue_service.state.current_index == 0

    def test_clear(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.clear()
        assert queue_service.state.count == 0
        assert queue_service.state.current_index == -1


class TestNavigationFailureAtomicity:
    """TD-008: failed playback candidates must never become observable state."""

    def _fail_load(self, monkeypatch, audio):
        attempts = []

        def failing_load(p):
            attempts.append(p)
            raise RuntimeError("load failed")

        monkeypatch.setattr(audio, "load", failing_load)
        return attempts

    def test_play_index_load_failure_preserves_index_and_propagates(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        attempts = self._fail_load(monkeypatch, fake_audio)

        with pytest.raises(RuntimeError, match="load failed"):
            queue_service.play_index(1)

        assert queue_service.state.current_index == 0
        assert attempts == [Path("/tmp/b.mp3")]
        assert playback_service.state.file_path == Path("/tmp/a.mp3")

    def test_play_index_failure_does_not_notify(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        calls = []

        def cb():
            calls.append(1)

        queue_service.subscribe_changed(cb)
        self._fail_load(monkeypatch, fake_audio)

        with pytest.raises(RuntimeError):
            queue_service.play_index(1)

        assert calls == []

    def test_next_failure_preserves_index(self, queue_service, fake_audio, monkeypatch):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        attempts = self._fail_load(monkeypatch, fake_audio)

        with pytest.raises(RuntimeError):
            queue_service.next()

        assert queue_service.state.current_index == 0
        assert attempts == [Path("/tmp/b.mp3")]

    def test_previous_failure_preserves_index(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        attempts = self._fail_load(monkeypatch, fake_audio)

        with pytest.raises(RuntimeError):
            queue_service.previous()

        assert queue_service.state.current_index == 1
        assert attempts == [Path("/tmp/a.mp3")]

    def test_play_failure_preserves_index(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        def failing_play():
            raise RuntimeError("play failed")

        monkeypatch.setattr(fake_audio, "play", failing_play)

        with pytest.raises(RuntimeError, match="play failed"):
            queue_service.play_index(1)

        assert queue_service.state.current_index == 0
        assert playback_service.state.file_path == Path("/tmp/a.mp3")

    def test_success_still_commits_all_three(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        loaded = []

        def recording_load(p):
            loaded.append(p)

        monkeypatch.setattr(fake_audio, "load", recording_load)

        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.next()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        queue_service.previous()
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        assert queue_service.state.current_index == 0
        assert loaded == [
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/a.mp3"),
        ]

    def test_failed_next_retry_plays_same_candidate(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        fail = {"on": True}

        def flaky_load(p):
            if fail["on"]:
                raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", flaky_load)

        with pytest.raises(RuntimeError):
            queue_service.next()

        assert queue_service.state.current_index == 0

        fail["on"] = False
        queue_service.next()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))

        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track.file_path == Path("/tmp/b.mp3")


class TestAsyncAcceptance:
    """TD-008B: queue index commits only on backend media acceptance."""

    def _commit_a(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

    def test_no_commit_before_acceptance(self, queue_service, fake_audio):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        assert queue_service.state.current_index == 0
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_async_rejection_preserves_queue(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "invalid media")
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_playback_never_claims_candidate_before_acceptance(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "bad")
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.error_message == "bad"

    def test_acceptance_commits_both_states_exactly_once(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        q_calls = []
        p_calls = []
        queue_service.subscribe_changed(lambda: q_calls.append(1))
        playback_service.subscribe_changed(lambda: p_calls.append(1))
        queue_service.next()
        assert q_calls == []  # queue not committed yet
        assert len(p_calls) == 1  # pending candidate registered
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert playback_service.state.file_path == Path("/tmp/b.mp3")
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert len(q_calls) == 1
        assert len(p_calls) == 2

    def test_late_success_from_superseded_candidate_ignored(
        self, queue_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)  # B pending
        queue_service.play_index(2)  # C supersedes B
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 0  # B did not commit
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2

    def test_late_rejection_from_superseded_candidate_does_not_corrupt(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)  # B pending
        queue_service.play_index(2)  # C supersedes B
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "stale failure")
        assert queue_service.state.current_index == 0
        assert playback_service.state.error_message is None
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.error_message is None

    def test_duplicate_acceptance_commits_once(self, queue_service, fake_audio):
        self._commit_a(queue_service, fake_audio)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.next()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert len(calls) == 1

    def test_stop_during_pending_prevents_resurrection(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        playback_service.stop()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 0
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_clear_during_pending_blocks_stale_commit(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        queue_service.clear()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.count == 0
        assert queue_service.state.current_index == -1
        assert playback_service.state.file_path == Path("/tmp/a.mp3")

    def test_queue_mutation_during_pending_commits_shifted_track(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        c_track = queue_service.state.tracks[2]
        queue_service.play_index(2)  # C pending at index 2
        queue_service.remove(0)  # a removed → C now sits at index 1
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        # Identity guard: C is still the same object → commits at its new index.
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track is c_track
        # Playback stays honest: C was genuinely accepted as the current media.
        assert playback_service.state.file_path == Path("/tmp/c.mp3")


class TestTruthfulPlaybackStatusInQueue:
    """TD-008B correction: acceptance commits queue/identity, never PLAYING."""

    def _commit_a(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

    def test_reject_before_playing_queue_stays_on_a(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "invalid media")
        assert queue_service.state.current_index == 0
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.status != PlaybackStatus.PLAYING
        assert playback_service.state.error_message == "invalid media"

    def test_runtime_rejection_after_acceptance_keeps_commit_no_duplicate_notify(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.next()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        calls = []
        playback_service.subscribe_changed(lambda: calls.append(1))
        # errorOccurred + InvalidMedia for the same source fire twice:
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "decode failed")
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "decode failed")
        assert queue_service.state.current_index == 1  # B stays committed
        assert playback_service.state.file_path == Path("/tmp/b.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "decode failed"
        assert len(calls) == 1  # no duplicate notify

    def test_auto_advance_accepts_b_not_playing_until_playing_state(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        queue_service.next()  # A ends → requests B
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert playback_service.state.file_path == Path("/tmp/b.mp3")
        assert playback_service.state.status != PlaybackStatus.PLAYING
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.PLAYING


class TestPendingTrackIdentity:
    """TD-015: pending candidates commit by track identity, never by index."""

    def _commit_a(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

    def test_shifted_pending_candidate_commits_at_new_index(
        self, queue_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        c_track = queue_service.state.tracks[2]
        queue_service.play_index(2)  # C pending at index 2
        queue_service.remove(1)  # B removed → C shifts to index 1
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track is c_track

    def test_pending_candidate_removed_stops_playback_and_drops_commit(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)  # B pending
        queue_service.remove(1)  # the pending track itself is removed
        # Removal cancels the pending request and stops playback.
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert fake_audio.state == "stopped"
        # Late acceptance must not resurrect B anywhere.
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")

    def test_unrelated_remove_does_not_cancel_pending(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        b_track = queue_service.state.tracks[1]
        queue_service.play_index(1)  # B pending
        queue_service.remove(2)  # C removed — unrelated to pending B
        assert queue_service.state.tracks[1] is b_track  # B still at index 1
        assert fake_audio.state == "playing"  # playback not stopped
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track is b_track

    def test_duplicate_file_paths_commit_exact_object(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/same.mp3"))  # B1 — distinct object, same path
        queue_service.add(Path("/tmp/same.mp3"))  # B2 — distinct object, same path
        queue_service.add(Path("/tmp/d.mp3"))
        target = queue_service.state.tracks[2]
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.play_index(2)  # pending = target (B2, same.mp3 at index 2)
        queue_service.remove(3)  # remove D — BOTH same.mp3 entries survive
        assert len(queue_service.state.tracks) == 3
        fake_audio.trigger_media_accepted(Path("/tmp/same.mp3"))
        # A path-only or value-equality search would find B1 (index 1) first;
        # identity must commit the exact B2 object at its current index.
        assert queue_service.state.current_index == 2
        assert queue_service.state.current_track is target

    def test_superseded_acceptance_blocked_by_identity_guard(
        self, queue_service, playback_service, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        callbacks = []

        def recording_load_and_play(path, on_accepted=None):
            callbacks.append((path, on_accepted))

        monkeypatch.setattr(playback_service, "load_and_play", recording_load_and_play)

        queue_service.play_index(1)  # B pending
        queue_service.play_index(2)  # C supersedes B
        b_path, b_cb = callbacks[0]
        c_path, c_cb = callbacks[1]
        b_cb(b_path)  # late acceptance of superseded B
        assert queue_service.state.current_index == -1  # B did not commit
        c_cb(c_path)
        assert queue_service.state.current_index == 2

    def test_clear_invalidates_pending(
        self, queue_service, playback_service, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        callbacks = []

        def recording_load_and_play(path, on_accepted=None):
            callbacks.append((path, on_accepted))

        monkeypatch.setattr(playback_service, "load_and_play", recording_load_and_play)

        queue_service.play_index(1)  # B pending
        b_path, b_cb = callbacks[0]
        queue_service.clear()
        b_cb(b_path)  # late acceptance after clear
        assert queue_service.state.count == 0
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None

    def test_sync_failure_clears_pending_bookkeeping(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        a_track = queue_service.state.tracks[0]
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        def failing_load(path):
            raise RuntimeError("load failed")

        monkeypatch.setattr(fake_audio, "load", failing_load)

        with pytest.raises(RuntimeError, match="load failed"):
            queue_service.play_index(1)

        queue_service.remove(1)  # removed track must not be treated as pending
        assert fake_audio.state == "playing"  # no stop() triggered
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))  # late acceptance
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track is a_track
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
