"""Tests for QueueService — sole authority over QueueState."""

import random
from pathlib import Path

import pytest

from michi.domain.playback import PlaybackStatus
from michi.domain.queue import RepeatMode


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


class TestRepeatModes:
    """M4 §18: end-of-media auto-advance driven by `RepeatMode`.

    Contract under test (NOT yet implemented in production):
    - `RepeatMode` (NONE/ONE/ALL) lives in `michi.domain.queue`;
    - `QueueState.repeat_mode: RepeatMode = RepeatMode.NONE`;
    - `PlaybackService` subscribes to the audio port's `subscribe_end_of_media`
      and re-exposes it as a service-level `subscribe_end_of_media(cb)`,
      forwarding only when a track is committed;
    - `QueueService` subscribes in __init__ and on end-of-media: ignores the
      event while a pending request exists (stale EOM); no-ops when the queue
      is empty or current_index < 0; otherwise by mode — NONE:
      play_index(current+1) if it exists else playback.stop(); ONE:
      play_index(current); ALL: play_index((current+1) % len).

    Tracks are committed via `play_index(i)` + `trigger_media_accepted`;
    end-of-track is driven via `trigger_end_of_media()`; an auto-advance
    candidate commits only after ITS acceptance trigger. "No advance
    happened" is asserted via `fake_audio.loaded` and load-count spying.
    """

    def test_repeat_none_middle_advances_to_next(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        fake_audio.trigger_end_of_media()  # NONE → auto-advance to index 1
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        assert queue_service.state.current_index == 0  # pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_repeat_none_last_stops(self, queue_service, playback_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

        fake_audio.trigger_end_of_media()  # NONE at last index → stop
        assert fake_audio.state == "stopped"
        assert queue_service.state.current_index == 1
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_repeat_one_middle_replays_same_entry(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        loads = []

        def recording_load(p):
            loads.append(p)
            fake_audio.loaded = p

        monkeypatch.setattr(fake_audio, "load", recording_load)
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert loads == [Path("/tmp/b.mp3")]

        queue_service.set_repeat_mode(RepeatMode.ONE)
        fake_audio.trigger_end_of_media()  # ONE → replay the same entry
        assert loads == [Path("/tmp/b.mp3"), Path("/tmp/b.mp3")]
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_repeat_one_last_replays(self, queue_service, fake_audio, monkeypatch):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        loads = []

        def recording_load(p):
            loads.append(p)
            fake_audio.loaded = p

        monkeypatch.setattr(fake_audio, "load", recording_load)
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert loads == [Path("/tmp/b.mp3")]

        queue_service.set_repeat_mode(RepeatMode.ONE)
        fake_audio.trigger_end_of_media()  # ONE → replay the last entry
        assert loads == [Path("/tmp/b.mp3"), Path("/tmp/b.mp3")]
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_repeat_all_middle_advances(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))

        queue_service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()  # ALL → advance to index 2
        assert fake_audio.loaded == Path("/tmp/c.mp3")
        assert queue_service.state.current_index == 1  # pending, not committed
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2

    def test_repeat_all_last_wraps_to_first(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2

        queue_service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()  # (2+1) % 3 == 0 → wrap to first
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

    def test_repeat_end_of_media_empty_queue_noop(self, queue_service, fake_audio):
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded is None
        assert queue_service.state.current_index == -1
        assert fake_audio.state == "stopped"  # nothing started, nothing stopped

    def test_repeat_single_track_queue(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        # NONE: no next entry → stop happens on EOM (terminal, no acceptance).
        queue_service.set_repeat_mode(RepeatMode.NONE)
        fake_audio.trigger_end_of_media()
        assert fake_audio.state == "stopped"
        assert queue_service.state.current_index == 0

        # Reset: play A again and commit.
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        # ONE: replay the only track.
        queue_service.set_repeat_mode(RepeatMode.ONE)
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        # Reset again.
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        # ALL: (0 + 1) % 1 == 0 → replays the only track.
        queue_service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

    def test_repeat_rejected_auto_advance_stops_no_loop(
        self, queue_service, fake_audio, monkeypatch
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        loads = []

        def recording_load(p):
            loads.append(p)
            fake_audio.loaded = p

        monkeypatch.setattr(fake_audio, "load", recording_load)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        fake_audio.trigger_end_of_media()  # NONE → auto-advance to B
        assert loads == [Path("/tmp/a.mp3"), Path("/tmp/b.mp3")]
        assert queue_service.state.current_index == 0  # pending, not committed

        fake_audio.trigger_media_rejected(Path("/tmp/b.mp3"), "broken")
        assert queue_service.state.current_index == 0  # rejection is terminal

        # Pending cleared: further EOMs must not re-advance or loop.
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_end_of_media()
        assert loads == [Path("/tmp/a.mp3"), Path("/tmp/b.mp3")]
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        assert queue_service.state.current_index == 0

    def test_repeat_stale_end_of_media_with_pending_ignored(
        self, queue_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

        queue_service.play_index(2)  # manual navigation → C pending at index 2
        assert queue_service.state.current_index == 0
        assert fake_audio.loaded == Path("/tmp/c.mp3")

        # Stale EOM while a manual request is in flight: must be ignored.
        # WITHOUT the pending guard, the auto-advance target (index 1, B)
        # differs from the pending one (index 2, C): play_index(1) would
        # supersede C and observable `fake_audio.loaded` would become b.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == Path("/tmp/c.mp3")  # C stays pending
        assert queue_service.state.current_index == 0  # no auto-advance to 1

        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2

    def test_repeat_stop_during_auto_advance_cancels_pending(
        self, queue_service, playback_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        fake_audio.trigger_end_of_media()  # auto-advance → B pending
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        playback_service.stop()  # external cancel (TD-016 terminal)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert (
            queue_service.state.current_index == 0
        )  # cancelled candidate never commits
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")

    def test_repeat_all_duplicate_paths_wrap_by_index(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/x.mp3"))
        queue_service.add(Path("/tmp/x.mp3"))  # distinct Track, same path
        queue_service.add(Path("/tmp/y.mp3"))
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(Path("/tmp/y.mp3"))
        assert queue_service.state.current_index == 2

        queue_service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()  # (2+1) % 3 == 0 → first entry
        assert fake_audio.loaded == Path("/tmp/x.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/x.mp3"))
        # By index (identity), not by path: index 0, not the duplicate at 1.
        assert queue_service.state.current_index == 0

    def test_repeat_rapid_mode_change_between_eom_and_acceptance(
        self, queue_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        queue_service.set_repeat_mode(RepeatMode.NONE)
        fake_audio.trigger_end_of_media()  # auto-advance to B (NONE)
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        queue_service.set_repeat_mode(RepeatMode.ONE)  # mid-flight mode change
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1  # in-flight request intact

        fake_audio.trigger_end_of_media()  # ONE now applies → replay B
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_repeat_duplicate_end_of_media_no_double_advance(
        self, queue_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))

        fake_audio.trigger_end_of_media()
        fake_audio.trigger_end_of_media()  # late duplicate — must not double-advance
        assert fake_audio.loaded == Path("/tmp/b.mp3")  # exactly ONE advance
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

        # A fresh EOM (not a duplicate) may advance again — only on acceptance.
        fake_audio.trigger_end_of_media()
        assert queue_service.state.current_index == 1  # candidate pending
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        assert queue_service.state.current_index == 2


class TestShuffleNavigation:
    """M4: shuffle navigation — deterministic via an injected, seeded RNG.

    Contract under test (NOT yet implemented in production):
    - `QueueState.shuffle_enabled: bool = False`;
    - `QueueService.__init__(playback_service, rng=None)` defaults to a
      fresh `random.Random`; tests inject a seeded RNG via `_shuffle_queue`;
    - `set_shuffle_enabled(True)` sets the flag (with notify), builds
      `pool = shuffled(tracks except current)` and `history = [current]`;
      disabling clears pool and history;
    - NEXT pops the pool (no repetition within a cycle); PREVIOUS walks real
      history and returns the current track to the pool; pool exhausted →
      repeat NONE stops, repeat ALL regenerates a cycle avoiding the track
      that just played, repeat ONE replays the current track untouched;
    - add enters the pool; remove drops the exact Track identity from both
      pool and history; clear wipes navigation;
    - an explicit play_index commit integrates (removed from pool, recorded
      in history); a rejected shuffled candidate is terminal and is dropped
      from the cycle.

    Determinism strategy: the exact pick order depends on the injected
    picker, so assertions pin the CONTRACT — cycle set-membership, identity
    resolution, and cross-service reproducibility for equal seeds — instead
    of hardcoding `random` output sequences.
    """

    def _shuffle_queue(self, playback_service, seed: int = 42):
        """QueueService with an injected seeded RNG for deterministic picks."""
        from michi.application.queue_service import QueueService

        return QueueService(playback_service, rng=random.Random(seed))

    def _populate(self, service, *paths: Path) -> None:
        for p in paths:
            service.add(p)

    def _commit_first(self, service, fake_audio, path: Path) -> None:
        service.play_index(0)
        fake_audio.trigger_media_accepted(path)

    def _track_index(self, service, path: Path) -> int:
        return [t.file_path for t in service.state.tracks].index(path)

    def test_shuffle_enabled_toggle_defaults_off(self, queue_service):
        assert queue_service.state.shuffle_enabled is False

    def test_enable_shuffle_keeps_committed_current(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        self._populate(
            service, Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        )
        self._commit_first(service, fake_audio, Path("/tmp/a.mp3"))
        assert service.state.current_index == 0

        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.set_shuffle_enabled(True)

        assert service.state.shuffle_enabled is True
        assert service.state.current_index == 0
        assert service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert calls == [1]  # the toggle notifies

    def test_shuffle_next_picks_without_repetition_until_cycle_done(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        picked = []
        for _ in range(2):  # two remaining pool entries
            service.next()
            path = fake_audio.loaded
            picked.append(path)
            fake_audio.trigger_media_accepted(path)

        # The cycle covered b and c exactly once each, never repeating a.
        assert set(picked) == {b, c}
        assert len(picked) == 2
        assert service.state.current_index in (1, 2)

        # Pool exhausted → repeat NONE → end-of-media stops playback.
        fake_audio.trigger_end_of_media()
        assert fake_audio.state == "stopped"
        assert service.state.current_index in (1, 2)  # last commit kept

    def test_shuffle_seeded_rng_deterministic_sequence(
        self, playback_service, fake_audio
    ):
        def sequence(seed: int):
            service = self._shuffle_queue(playback_service, seed=seed)
            self._populate(
                service,
                Path("/tmp/a.mp3"),
                Path("/tmp/b.mp3"),
                Path("/tmp/c.mp3"),
            )
            self._commit_first(service, fake_audio, Path("/tmp/a.mp3"))
            service.set_shuffle_enabled(True)
            seq = []
            for _ in range(2):
                service.next()
                path = fake_audio.loaded
                seq.append(path)
                fake_audio.trigger_media_accepted(path)
            return seq

        first = sequence(7)
        second = sequence(7)

        # Two independent services with equal seeds draw identical sequences.
        assert first == second
        assert set(first) == {Path("/tmp/b.mp3"), Path("/tmp/c.mp3")}

    def test_shuffle_previous_walks_history(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.next()
        first_pick = fake_audio.loaded
        fake_audio.trigger_media_accepted(first_pick)
        service.next()
        second_pick = fake_audio.loaded
        fake_audio.trigger_media_accepted(second_pick)
        assert first_pick != second_pick  # no repetition within the cycle

        # PREVIOUS walks real history → target is the previous committed
        # pick, never a fresh random draw.
        service.previous()
        assert fake_audio.loaded == first_pick
        fake_audio.trigger_media_accepted(first_pick)
        assert service.state.current_index == self._track_index(service, first_pick)

        # The track left behind returned to the pool: a later next() may
        # select it again.
        service.next()
        assert fake_audio.loaded == second_pick
        fake_audio.trigger_media_accepted(second_pick)
        assert service.state.current_index == self._track_index(service, second_pick)

    def test_shuffle_pool_exhausted_repeat_all_new_cycle(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.set_repeat_mode(RepeatMode.ALL)

        # Consume the two pool entries via end-of-media auto-advance.
        for _ in range(2):
            fake_audio.trigger_end_of_media()
            picked = fake_audio.loaded
            assert picked in (b, c)
            fake_audio.trigger_media_accepted(picked)
        last_played = fake_audio.loaded
        assert last_played in (b, c)

        # Pool exhausted → repeat ALL regenerates a cycle that avoids the
        # track that just played: a fresh pick happens, never a repetition.
        fake_audio.trigger_end_of_media()
        new_pick = fake_audio.loaded
        assert new_pick != last_played
        assert new_pick in (a, b, c)
        fake_audio.trigger_media_accepted(new_pick)
        assert service.state.current_index == self._track_index(service, new_pick)

    def test_shuffle_pool_exhausted_repeat_one_replays_current(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.set_repeat_mode(RepeatMode.ONE)

        # While the pool has entries, EVERY mode still pops the pool.
        for _ in range(2):
            fake_audio.trigger_end_of_media()
            picked = fake_audio.loaded
            assert picked in (b, c)
            fake_audio.trigger_media_accepted(picked)
        current = fake_audio.loaded  # committed second pick

        # Pool exhausted → repeat ONE replays the current track.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == current
        fake_audio.trigger_media_accepted(current)
        assert service.state.current_index == self._track_index(service, current)

        # Pool/history untouched: a further EOM replays current again.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == current

    def test_shuffle_pool_exhausted_repeat_none_stops(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        for _ in range(2):
            fake_audio.trigger_end_of_media()
            picked = fake_audio.loaded
            assert picked in (b, c)
            fake_audio.trigger_media_accepted(picked)
        last_index = service.state.current_index

        # Pool exhausted → repeat NONE → end-of-media stops playback.
        fake_audio.trigger_end_of_media()
        assert fake_audio.state == "stopped"
        assert service.state.current_index == last_index

    def test_shuffle_single_track_queue(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a = Path("/tmp/a.mp3")
        service.add(a)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)  # pool is empty immediately

        # Repeat ALL with a single track: the empty pool regenerates to the
        # only track (single-track edge) and replays it.
        service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

        # Repeat NONE with an empty pool stops.
        service.set_repeat_mode(RepeatMode.NONE)
        fake_audio.trigger_end_of_media()
        assert fake_audio.state == "stopped"
        assert service.state.current_index == 0

    def test_shuffle_add_enters_pool(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.add(c)  # pool was {b}; now {b, c}

        picked = []
        for _ in range(2):
            service.next()
            path = fake_audio.loaded
            picked.append(path)
            fake_audio.trigger_media_accepted(path)
        assert set(picked) == {b, c}  # c entered the pool and was selectable

    def test_shuffle_remove_identity_from_pool_and_history(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.next()
        first_pick = fake_audio.loaded
        fake_audio.trigger_media_accepted(first_pick)
        remaining = next(p for p in (b, c) if p != first_pick)

        # Remove the track still sitting in the pool: exact identity leaves
        # both the queue and the pool.
        service.remove(self._track_index(service, remaining))
        assert remaining not in [t.file_path for t in service.state.tracks]

        # The dropped track is never re-picked: repeat ALL regenerates from
        # the current tracks, which no longer contain the removed object.
        service.set_repeat_mode(RepeatMode.ALL)
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded != remaining
        assert fake_audio.loaded == a  # the only track left for the cycle
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

    def test_shuffle_clear_resets_navigation(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.next()
        picked = fake_audio.loaded
        fake_audio.trigger_media_accepted(picked)

        service.clear()
        assert service.state.count == 0
        assert service.state.current_index == -1
        assert fake_audio.state == "stopped"

        # Fresh queue state: stale end-of-media events are inert — nothing
        # advances from the wiped navigation.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == picked
        assert service.state.current_index == -1

        # Re-enabling rebuilds navigation from the new tracks: the pool
        # excludes the committed current track.
        d, e = Path("/tmp/d.mp3"), Path("/tmp/e.mp3")
        service.add(d)
        service.add(e)
        self._commit_first(service, fake_audio, d)
        service.set_shuffle_enabled(False)
        service.set_shuffle_enabled(True)
        service.next()
        assert fake_audio.loaded == e  # current (d) excluded from the pool

    def test_shuffle_explicit_play_index_integrates(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.play_index(2)  # explicit user choice: c
        fake_audio.trigger_media_accepted(c)
        assert service.state.current_index == 2
        assert service.state.current_track.file_path == c

        # The explicitly committed track was removed from the pool and
        # recorded in history: next() must not re-pick c.
        service.next()
        assert fake_audio.loaded == b  # only b remained in the pool
        fake_audio.trigger_media_accepted(b)
        assert service.state.current_index == 1

    def test_shuffle_duplicates_navigate_by_identity(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        x, y = Path("/tmp/x.mp3"), Path("/tmp/y.mp3")
        service.add(x)  # index 0 — x1, committed first
        service.add(x)  # index 1 — x2, distinct object, same path
        service.add(y)  # index 2
        self._commit_first(service, fake_audio, x)
        service.set_shuffle_enabled(True)

        picked_indices = []
        for _ in range(2):  # pool = {x2, y}: each picked exactly once
            service.next()
            path = fake_audio.loaded
            fake_audio.trigger_media_accepted(path)
            idx = service.state.current_index
            picked_indices.append(idx)
            # Exact identity: the commit lands on the picked object's index.
            assert service.state.tracks[idx].file_path == path

        # Both distinct pool objects were consumed — never the committed x1
        # at index 0, and never a path-confused resolution.
        assert sorted(picked_indices) == [1, 2]

    def test_shuffle_previous_then_next_coherence(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.next()
        first_pick = fake_audio.loaded
        fake_audio.trigger_media_accepted(first_pick)
        assert service.state.current_index == self._track_index(service, first_pick)

        # PREVIOUS is deterministic: it walks history back to a — never a
        # random draw from the pool.
        service.previous()
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

        # The returned track joined the untouched third track in the pool:
        # next() may select either, but never the committed current (a).
        service.next()
        second_pick = fake_audio.loaded
        assert second_pick in (b, c)
        fake_audio.trigger_media_accepted(second_pick)
        assert service.state.current_index == self._track_index(service, second_pick)

    def test_shuffle_rejected_candidate_dropped_from_cycle(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        fake_audio.trigger_end_of_media()  # auto-advance pops a pool candidate
        rejected = fake_audio.loaded
        assert rejected in (b, c)
        assert service.state.current_index == 0  # pending, not committed

        fake_audio.trigger_media_rejected(rejected, "broken")
        assert service.state.current_index == 0  # rejection is terminal
        assert service.state.current_track.file_path == a
        assert fake_audio.state == "stopped"
        assert fake_audio.loaded == rejected  # no immediate retry

        # Stale EOMs after rejection stay inert (TD-008B intent guard) — the
        # dropped candidate is never re-picked automatically.
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == rejected

        # The rejected candidate is dropped from the cycle: the next pick
        # comes from the remaining pool only.
        service.next()
        assert fake_audio.loaded != rejected
        assert fake_audio.loaded in (b, c)
        fake_audio.trigger_media_accepted(fake_audio.loaded)
        assert service.state.current_index == self._track_index(
            service, fake_audio.loaded
        )

    def test_shuffle_disable_restores_natural_order(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)

        service.set_shuffle_enabled(False)
        assert service.state.shuffle_enabled is False

        # Natural order resumes: next() is index+1 again.
        service.next()
        assert fake_audio.loaded == b
        fake_audio.trigger_media_accepted(b)
        assert service.state.current_index == 1

    def test_shuffle_toggle_off_on_fresh_cycle(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.next()
        first_pick = fake_audio.loaded
        fake_audio.trigger_media_accepted(first_pick)

        service.set_shuffle_enabled(False)
        assert service.state.shuffle_enabled is False
        service.set_shuffle_enabled(True)  # rebuilds a fresh cycle
        assert service.state.shuffle_enabled is True

        # A pick occurs from the rebuilt pool; the committed current track is
        # excluded, but previously played tracks may re-enter.
        service.next()
        assert fake_audio.loaded in (a, b, c)
        assert fake_audio.loaded != first_pick  # current excluded from pool
        fake_audio.trigger_media_accepted(fake_audio.loaded)
        assert service.state.current_index == self._track_index(
            service, fake_audio.loaded
        )
