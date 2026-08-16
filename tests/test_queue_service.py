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

        def recording_load_and_play(
            path, on_accepted=None, on_rejected=None, on_cancelled=None
        ):
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

        def recording_load_and_play(
            path, on_accepted=None, on_rejected=None, on_cancelled=None
        ):
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


class TestRejectedRequestIsTerminal:
    """TD-015: a rejected pending request is terminal — removing its track
    must not trigger a spurious playback stop."""

    def _commit_a(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

    def test_remove_after_rejection_does_not_stop_playback(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)  # B pending
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "rejected")
        playback_service.update_position(30000)
        stop_calls = []
        real_stop = playback_service.stop

        def spy_stop():
            stop_calls.append(1)
            real_stop()

        monkeypatch.setattr(playback_service, "stop", spy_stop)
        queue_service.remove(1)
        assert stop_calls == []  # request already terminal: no spurious stop
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "rejected"
        assert playback_service.state.position_ms == 30000  # no second-stop reset

    def test_rejected_request_can_be_retried(self, queue_service, fake_audio):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "bad")
        assert queue_service.state.current_index == 0
        queue_service.play_index(1)  # retry the same index
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track.file_path == Path("/tmp/b.mp3")

    def test_superseded_rejection_does_not_clear_latest_pending(
        self, queue_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)  # B pending
        queue_service.play_index(2)  # C supersedes B
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "stale")
        assert queue_service.state.current_index == 0  # nothing cleared
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2
        assert queue_service.state.current_track.file_path == Path("/tmp/c.mp3")

    def test_runtime_rejection_after_acceptance_does_not_roll_back_queue(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "decode failed")
        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track.file_path == Path("/tmp/b.mp3")
        assert playback_service.state.file_path == Path("/tmp/b.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "decode failed"

    def test_stop_then_late_rejection_leaves_queue_untouched(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(1)  # B pending
        playback_service.stop()
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "late")
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.error_message is None


class TestCancellationTerminal:
    """TD-016: a stopped request is terminal for the queue.

    `PlaybackService.stop()` clears its own pending request but never
    notifies the requestor, so `QueueService._pending_track` keeps pointing
    at the track that was pending — and a later `remove()` of that track
    issues a REDUNDANT second `stop()`. The target contract: a pending
    request terminates in exactly one of ACCEPTED / REJECTED / CANCELLED /
    SUPERSEDED; `load_and_play` gains an `on_cancelled` callback that
    `stop()` invokes at most once for the exact pending path; `QueueService`
    passes it and clears `_pending_track` only when the cancelled Track IS
    the pending one (exact identity + file_path match), without mutating
    state, changing current_index, removing the track, issuing another stop,
    or notifying when public state is unchanged."""

    def _pending_b(self, queue_service, playback_service, fake_audio):
        """Commit A at index 0, then leave B pending at index 1."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.play_index(1)

    def _stop_spy(self, playback_service, monkeypatch):
        calls = []
        real_stop = playback_service.stop

        def spy():
            calls.append(1)
            real_stop()

        monkeypatch.setattr(playback_service, "stop", spy)
        return calls

    def _load_and_play_spy(self, playback_service, monkeypatch):
        """Record kwargs of every load_and_play call and forward them."""
        captured = []
        orig = playback_service.load_and_play

        def spy(path, **kwargs):
            captured.append(kwargs)
            orig(path, **kwargs)

        monkeypatch.setattr(playback_service, "load_and_play", spy)
        return captured

    def _cancel_counting_spy(self, playback_service, monkeypatch):
        """Spy on load_and_play; wrap on_cancelled so invocations are counted
        while the queue's real callback still runs."""
        captured = []
        cancellations = []
        orig = playback_service.load_and_play

        def spy(path, **kwargs):
            on_cancelled = kwargs.get("on_cancelled")
            if on_cancelled is not None:

                def wrapped(p):
                    cancellations.append(p)
                    on_cancelled(p)

                kwargs["on_cancelled"] = wrapped
            captured.append(kwargs)
            orig(path, **kwargs)

        monkeypatch.setattr(playback_service, "load_and_play", spy)
        return captured, cancellations

    def test_stop_clears_queue_pending(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """External stop cancels the request; removing the pending track
        afterwards must NOT issue a redundant second stop."""
        self._pending_b(queue_service, playback_service, fake_audio)
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        playback_service.stop()  # the external cancellation route
        queue_service.remove(1)  # remove the track that was pending
        assert len(stop_calls) == 1  # only the cancel — remove adds no second
        assert [t.file_path for t in queue_service.state.tracks] == [Path("/tmp/a.mp3")]
        assert queue_service.state.current_index == 0

    def test_remove_after_cancel_no_redundant_stop(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """Same scenario: the remove itself must succeed and stay silent."""
        self._pending_b(queue_service, playback_service, fake_audio)
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        playback_service.stop()
        queue_service.remove(1)
        assert len(stop_calls) == 1  # no redundant second stop
        assert [t.file_path for t in queue_service.state.tracks] == [Path("/tmp/a.mp3")]

    def test_accepted_path_still_commits(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """Regression guard: acceptance still commits and clears pending."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.play_index(1)  # B pending
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        queue_service.remove(2)  # unrelated, non-pending
        assert stop_calls == []

    def test_rejected_still_clears_pending(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """Regression guard: rejection is terminal and clears pending."""
        self._pending_b(queue_service, playback_service, fake_audio)
        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "err")
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        queue_service.remove(1)
        assert stop_calls == []

    def test_late_cancel_does_not_clear_superseding_candidate(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """A late cancellation of a superseded candidate must not clear the
        current pending one."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        captured = self._load_and_play_spy(playback_service, monkeypatch)
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        queue_service.play_index(1)  # B pending
        queue_service.play_index(2)  # C supersedes B
        assert captured[0].get("on_cancelled") is not None  # TD-016 API
        # Late cancellation of the superseded B: C must stay pending.
        captured[0]["on_cancelled"](Path("/tmp/b.mp3"))
        queue_service.remove(2)  # C is still pending → remove still stops
        assert len(stop_calls) == 1

    def test_duplicate_paths_cancel_resolves_exact_identity(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """Cancellation resolves by exact Track identity, never by path:
        a callback captured from a different (same-path) object must not
        clear the current pending one."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/same.mp3"))  # B1 — distinct object
        queue_service.add(Path("/tmp/same.mp3"))  # B2 — distinct object
        captured = self._load_and_play_spy(playback_service, monkeypatch)
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        queue_service.play_index(1)  # B1 pending
        queue_service.play_index(2)  # B2 supersedes B1
        assert captured[0].get("on_cancelled") is not None  # TD-016 API
        # Cancel carrying B1's callback and B1's path: B2 must stay pending.
        captured[0]["on_cancelled"](Path("/tmp/same.mp3"))
        queue_service.remove(2)  # B2 still pending → remove still stops
        assert len(stop_calls) == 1
        # A correct cancel for the exact pending B2 clears it.
        queue_service.add(Path("/tmp/same.mp3"))  # B2' at index 2
        queue_service.play_index(2)
        captured[2]["on_cancelled"](Path("/tmp/same.mp3"))
        queue_service.remove(2)  # pending already cleared → no stop
        assert len(stop_calls) == 1
        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/tmp/a.mp3"),
            Path("/tmp/same.mp3"),
        ]

    def test_stop_without_pending_no_false_cancel(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """stop() with nothing pending must never invoke on_cancelled and
        must leave queue public state and notifications untouched."""
        queue_service.add(Path("/tmp/a.mp3"))
        captured, cancellations = self._cancel_counting_spy(
            playback_service, monkeypatch
        )
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        # Request accepted: nothing is pending, callbacks dropped.
        notify = []
        queue_service.subscribe_changed(lambda: notify.append(1))
        playback_service.stop()
        assert cancellations == []  # no pending → on_cancelled never invoked
        assert queue_service.state.current_index == 0
        assert [t.file_path for t in queue_service.state.tracks] == [Path("/tmp/a.mp3")]
        assert notify == []  # public state unchanged → no queue notification

    def test_repeated_stop_cancels_at_most_once(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        """Two external stops must invoke on_cancelled at most once and must
        not leave a phantom pending that a later remove() re-stops."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        captured, cancellations = self._cancel_counting_spy(
            playback_service, monkeypatch
        )
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.play_index(1)  # B pending
        assert captured[1].get("on_cancelled") is not None  # TD-016 API
        stop_calls = self._stop_spy(playback_service, monkeypatch)
        notify = []
        queue_service.subscribe_changed(lambda: notify.append(1))
        p_notify = []
        playback_service.subscribe_changed(lambda: p_notify.append(1))
        playback_service.stop()
        playback_service.stop()
        assert len(cancellations) == 1  # at-most-once: second stop re-fires nothing
        assert notify == []  # cancellation mutated no public queue state
        assert len(p_notify) == 2  # one playback notify per external stop
        queue_service.remove(1)  # pending already cleared → no third stop
        assert len(stop_calls) == 2

    def test_late_media_accepted_after_stop_no_resurrection(
        self, queue_service, playback_service, fake_audio
    ):
        """Regression guard: late acceptance after stop() must not resurrect
        the cancelled candidate anywhere."""
        self._pending_b(queue_service, playback_service, fake_audio)
        playback_service.stop()
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
        ]
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_late_playing_state_after_stop_blocked(
        self, queue_service, playback_service, fake_audio
    ):
        """Regression guard: a late PLAYING state after stop() is blocked by
        the intent guard."""
        self._pending_b(queue_service, playback_service, fake_audio)
        playback_service.stop()
        fake_audio.trigger_playback_state(PlaybackStatus.PLAYING)
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_reentrant_same_object_rerrequest_survives_stop(
        self, queue_service, playback_service, fake_audio
    ):
        """A subscriber that synchronously re-requests the SAME Track during
        stop()'s notify installs a new pending; the stale cancellation from
        the outer stop must not clear it, so the re-requested track still
        commits (no queue/playback divergence)."""
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.play_index(1)  # B pending (same object re-requested below)
        re_requested = []

        def _re_request() -> None:
            # Fire at most once: the nested load_and_play in stop()'s notify
            # would otherwise re-trigger this subscriber endlessly.
            if re_requested:
                return
            re_requested.append(1)
            queue_service.play_index(1)

        playback_service.subscribe_changed(_re_request)
        playback_service.stop()  # notify re-requests B; stale cancel must not clear it
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1
        assert playback_service.state.file_path == Path("/tmp/b.mp3")
