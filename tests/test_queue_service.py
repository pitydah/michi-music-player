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
        """Repeat ONE takes precedence over shuffle at end-of-media.

        Contract change (LOCAL-STABILIZATION-01.6.1): the OLD rule encoded
        "while the pool has entries, EVERY mode pops the pool". The canonical
        rule is: with shuffle ON + repeat ONE, an end-of-media replays the
        EXACT current entry while the shuffle pool is still NON-EMPTY — the
        pool is NOT popped (A → A, never A → B/C). The exhaustion case (pool
        empty + ONE) also replays the current entry, unchanged.
        """
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)  # pool = {b, c} — non-empty
        service.set_repeat_mode(RepeatMode.ONE)

        # ONE precedes shuffle: EOM replays the current entry (a); the
        # non-empty pool {b, c} is NOT popped.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a
        assert service.state.current_index == 0  # pending, not committed
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

        # Exhaustion case: consume the pool through manual navigation, then
        # ONE on an empty pool still replays the current entry.
        service.next()
        picked = fake_audio.loaded
        assert picked in (b, c)
        fake_audio.trigger_media_accepted(picked)
        service.next()
        remaining = next(p for p in (b, c) if p != picked)
        assert fake_audio.loaded == remaining
        fake_audio.trigger_media_accepted(remaining)
        current = fake_audio.loaded  # committed second pick

        fake_audio.trigger_end_of_media()  # empty pool + ONE → replay current
        assert fake_audio.loaded == current
        fake_audio.trigger_media_accepted(current)
        assert service.state.current_index == self._track_index(service, current)

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


class TestRepeatOneShufflePrecedence:
    """LOCAL-STABILIZATION-01.6.1: repeat ONE takes precedence over shuffle.

    At end-of-media, ONE replays the EXACT current queue entry regardless of
    any remaining shuffle pool (A → A, never A → B/C) — the pool is NOT
    popped. Manual NEXT/PREVIOUS remain user navigation: ONE does not trap
    them, so they keep their shuffle-pool / natural-order semantics.
    """

    def _shuffle_queue(self, playback_service, seed: int = 42):
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

    def test_repeat_one_with_shuffle_non_empty_pool_replays_current(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)  # pool = {b, c}
        service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a  # current replays, NOT b/c
        assert service.state.current_index == 0  # pending, not committed
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

    def test_repeat_one_with_shuffle_single_track(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a = Path("/tmp/a.mp3")
        service.add(a)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)  # empty pool immediately
        service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

    def test_repeat_one_with_shuffle_duplicate_paths(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        x, y = Path("/tmp/x.mp3"), Path("/tmp/y.mp3")
        service.add(x)  # index 0 — x1, committed first
        service.add(x)  # index 1 — x2, distinct object, same path
        service.add(y)  # index 2
        self._commit_first(service, fake_audio, x)
        service.set_shuffle_enabled(True)  # pool = {x2, y}
        service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == x
        fake_audio.trigger_media_accepted(x)
        # Exact identity: the committed current stays the FIRST entry (x1),
        # never a path match on the duplicate x2 sitting in the pool.
        assert service.state.current_index == 0
        assert service.state.current_track is service.state.tracks[0]

    def test_repeat_one_after_prior_shuffled_navigation(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)  # pool = {b, c}
        service.set_repeat_mode(RepeatMode.ONE)

        # ONE EOM replays the current entry; the pool is NOT popped.
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a
        assert {t.file_path for t in service._navigator.pool} == {b, c}
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

        # Switching to NONE restores pool semantics: the untouched pool
        # {b, c} still yields an auto-advance.
        service.set_repeat_mode(RepeatMode.NONE)
        fake_audio.trigger_end_of_media()
        picked = fake_audio.loaded
        assert picked in (b, c)
        fake_audio.trigger_media_accepted(picked)
        assert service.state.current_index != 0

    def test_changing_one_to_none_restores_shuffle_pool(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()  # ONE → replay a
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

        service.set_repeat_mode(RepeatMode.NONE)
        fake_audio.trigger_end_of_media()  # NONE + shuffle → pool pick
        picked = fake_audio.loaded
        assert picked in (b, c)
        assert picked != a
        fake_audio.trigger_media_accepted(picked)
        assert service.state.current_index != 0

    def test_changing_one_to_all_wraps(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.set_repeat_mode(RepeatMode.ONE)
        service.set_repeat_mode(RepeatMode.ALL)  # ONE no longer applies

        fake_audio.trigger_end_of_media()  # ALL + shuffle → pool pick
        picked = fake_audio.loaded
        assert picked in (b, c)  # not a replay of a
        assert picked != a
        fake_audio.trigger_media_accepted(picked)
        assert service.state.current_index != 0

    def test_manual_next_not_trapped_by_repeat_one(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.set_repeat_mode(RepeatMode.ONE)

        queue_service.next()  # user navigation, NOT a replay
        assert fake_audio.loaded == Path("/tmp/b.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1

    def test_manual_previous_not_trapped_by_repeat_one(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        queue_service.set_repeat_mode(RepeatMode.ONE)

        queue_service.previous()  # user navigation
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == 0

    def test_manual_next_with_shuffle_and_one_picks_pool(
        self, playback_service, fake_audio
    ):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        self._populate(service, a, b, c)
        self._commit_first(service, fake_audio, a)
        service.set_shuffle_enabled(True)
        service.set_repeat_mode(RepeatMode.ONE)

        service.next()  # manual NEXT keeps pool semantics under ONE
        picked = fake_audio.loaded
        assert picked in (b, c)  # seeded rng → deterministic pool draw
        assert picked != a
        fake_audio.trigger_media_accepted(picked)
        assert service.state.current_index != 0

    def test_repeat_one_async_acceptance_still_atomic(
        self, queue_service, playback_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()  # ONE → replay a, pending
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        assert queue_service.state.current_index == 0

        # M4-FINAL-CORRECTION: removal of the committed current no longer
        # fabricates a relocated current (index -1, current_track None); the
        # late acceptance does not commit. The pending branch still stops
        # playback (TD-015).
        queue_service.remove(0)  # the pending track itself is removed
        assert [t.file_path for t in queue_service.state.tracks] == [Path("/tmp/b.mp3")]
        assert queue_service.state.current_index == -1  # no fictitious current
        assert queue_service.state.current_track is None

        # Late acceptance of the removed candidate must not commit anywhere
        # (identity guard): current_index is not set to a stale index.
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None
        assert playback_service.state.status == PlaybackStatus.STOPPED

    def test_repeat_one_rejection_still_terminal(
        self, queue_service, playback_service, fake_audio, monkeypatch
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
        assert loads == [Path("/tmp/a.mp3")]
        queue_service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()  # ONE → replay a, pending
        assert loads == [Path("/tmp/a.mp3"), Path("/tmp/a.mp3")]
        assert queue_service.state.current_index == 0

        fake_audio.trigger_media_rejected(Path("/tmp/a.mp3"), "broken")
        assert queue_service.state.current_index == 0  # rejection is terminal
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert playback_service.state.error_message == "broken"

        # Pending cleared + playback intent lapsed: further EOMs do nothing.
        fake_audio.trigger_end_of_media()
        fake_audio.trigger_end_of_media()
        assert loads == [Path("/tmp/a.mp3"), Path("/tmp/a.mp3")]
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        assert queue_service.state.current_index == 0

    def test_repeat_one_cancellation_still_terminal(
        self, queue_service, playback_service, fake_audio
    ):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        queue_service.set_repeat_mode(RepeatMode.ONE)

        fake_audio.trigger_end_of_media()  # ONE → replay a, pending
        assert fake_audio.loaded == Path("/tmp/a.mp3")
        assert queue_service.state.current_index == 0

        playback_service.stop()  # external cancel → on_cancelled clears pending
        fake_audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        # The cancelled candidate never commits: no stale commit.
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track.file_path == Path("/tmp/a.mp3")
        assert playback_service.state.status == PlaybackStatus.STOPPED


class TestQueueMove:
    """M4 Original Closeout: queue reorder (`move`) — exact Track identity,
    committed-current recompute, pending-track preservation, no playback
    side effects, exactly one notification, deterministic invalid moves,
    shuffle navigator integrity.

    Contract under test (NOT yet implemented in production):
    - `QueueService.move(from_index, to_index) -> None` moves the EXACT Track
      object by identity — never recreates, never path-compares;
    - the committed current Track identity is preserved: `current_index` is
      recomputed by identity after the reorder; the pending Track identity is
      preserved: acceptance after the reorder commits at the NEW index;
    - a successful reorder never stops/loads/restarts playback and fires
      EXACTLY ONE notification;
    - invalid moves (out-of-range) and same-index moves are deterministic
      no-ops that fire NO notification;
    - duplicates resolve by exact object identity, never by path;
    - the shuffle navigator pool/history are NOT regenerated or corrupted by
      the physical list reorder (objects are identity-based).
    """

    def _shuffle_queue(self, playback_service, seed: int = 42):
        from michi.application.queue_service import QueueService

        return QueueService(playback_service, rng=random.Random(seed))

    def _paths(self, service) -> list:
        return [t.file_path for t in service.state.tracks]

    def test_move_forward(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(0, 2)
        assert self._paths(queue_service) == [b, c, a, d]
        assert queue_service.state.count == 4
        assert calls == [1]  # EXACTLY ONE notification

    def test_move_backward(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(3, 1)
        assert self._paths(queue_service) == [a, d, b, c]
        assert calls == [1]

    def test_move_first_to_last(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        queue_service.move(0, 3)
        assert self._paths(queue_service) == [b, c, d, a]

    def test_move_last_to_first(self, queue_service):
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c, d):
            queue_service.add(p)
        queue_service.move(3, 0)
        assert self._paths(queue_service) == [d, a, b, c]

    def test_move_same_index_noop(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(1, 1)
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []  # same-index → no-op, ZERO notify

    def test_move_invalid_negative(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(-1, 2)  # out-of-range source → deterministic no-op
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []

    def test_move_invalid_destination(self, queue_service):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.move(1, 99)  # out-of-range destination → deterministic no-op
        assert self._paths(queue_service) == [a, b, c]
        assert calls == []

    def test_move_current_track_preserves_identity(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        b_track = queue_service.state.tracks[1]
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(b)
        loaded_before = fake_audio.loaded
        queue_service.move(1, 0)
        assert queue_service.state.current_index == 0
        assert queue_service.state.current_track is b_track  # identity, not path
        assert fake_audio.loaded == loaded_before  # no playback reload
        assert fake_audio.state == "playing"  # no stop

    def test_move_track_before_current_after(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        b_track = queue_service.state.tracks[1]
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(b)
        queue_service.move(0, 2)  # [a, b, c] → [b, c, a]
        assert self._paths(queue_service) == [b, c, a]
        assert queue_service.state.current_index == 0  # recomputed by identity
        assert queue_service.state.current_track is b_track

    def test_move_track_after_current_before(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        b_track = queue_service.state.tracks[1]
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(b)
        queue_service.move(2, 0)  # [a, b, c] → [c, a, b]
        assert self._paths(queue_service) == [c, a, b]
        assert queue_service.state.current_index == 2  # recomputed by identity
        assert queue_service.state.current_track is b_track

    def test_move_no_playback_reload(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        loads = []
        orig = playback_service.load_and_play

        def spy(path, **kwargs):
            loads.append(path)
            orig(path, **kwargs)

        monkeypatch.setattr(playback_service, "load_and_play", spy)
        loaded_before = fake_audio.loaded
        queue_service.move(1, 2)
        assert loads == []  # move must never call load_and_play
        assert fake_audio.loaded == loaded_before

    def test_move_no_playback_stop(
        self, queue_service, playback_service, fake_audio, monkeypatch
    ):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        assert fake_audio.state == "playing"
        stops = []
        orig_stop = playback_service.stop

        def spy_stop():
            stops.append(1)
            orig_stop()

        monkeypatch.setattr(playback_service, "stop", spy_stop)
        queue_service.move(1, 2)
        assert stops == []  # no stop() call
        assert fake_audio.state == "playing"  # playback untouched

    def test_move_pending_then_accepted(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)  # a committed
        b_track = queue_service.state.tracks[1]
        queue_service.play_index(1)  # b pending
        queue_service.move(1, 2)  # [a, c, b]
        assert self._paths(queue_service) == [a, c, b]
        fake_audio.trigger_media_accepted(b)
        assert queue_service.state.current_index == 2  # commits at the NEW index
        assert queue_service.state.current_track is b_track  # identity
        assert queue_service._pending_track is None  # pending cleared

    def test_move_pending_then_rejected(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        queue_service.play_index(1)  # b pending
        queue_service.move(1, 2)  # [a, c, b]
        fake_audio.trigger_media_rejected(b, "broken")
        assert self._paths(queue_service) == [a, c, b]  # reorder kept
        assert queue_service.state.current_index == 0  # current stays 0
        assert queue_service.state.current_track.file_path == a
        assert queue_service._pending_track is None  # pending cleared

    def test_move_pending_then_cancelled(
        self, queue_service, playback_service, fake_audio
    ):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        queue_service.play_index(1)  # b pending
        queue_service.move(1, 2)  # [a, c, b]
        playback_service.stop()  # external cancel → on_cancelled clears pending
        fake_audio.trigger_media_accepted(b)
        assert queue_service.state.current_index == 0  # NOT committed
        assert queue_service.state.current_track.file_path == a

    def test_move_superseded_pending_callback(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        queue_service.play_index(1)  # b pending
        queue_service.play_index(2)  # c supersedes b — b's callbacks dropped
        c_track = queue_service.state.tracks[2]
        queue_service.move(0, 2)  # [b, c, a] — c relocates to index 1
        assert self._paths(queue_service) == [b, c, a]
        fake_audio.trigger_media_accepted(c)  # late acceptance of the live pending
        assert queue_service.state.current_track is c_track  # c commits
        assert queue_service.state.current_index == 1  # at c's NEW index
        # The superseded b never commits.
        assert queue_service.state.tracks[0].file_path == b

    def test_move_duplicates_exact_identity(self, queue_service, fake_audio):
        x, y = Path("/tmp/x.mp3"), Path("/tmp/y.mp3")
        queue_service.add(x)  # index 0 — x1
        queue_service.add(x)  # index 1 — x2, distinct object, same path
        queue_service.add(y)  # index 2
        x1 = queue_service.state.tracks[0]
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(x)
        queue_service.move(1, 2)  # [x1, y, x2]
        assert self._paths(queue_service) == [x, y, x]
        assert queue_service.state.current_index == 0
        # Exact identity: never path-matched to the duplicate x2 at index 2.
        assert queue_service.state.current_track is x1

    def test_move_shuffle_pool_unchanged(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b, c}, history = [a]
        pool_ids = {id(t) for t in service._navigator.pool}
        history_ids = {id(t) for t in service._navigator.history}
        service.move(1, 2)  # physical reorder
        # The navigator holds the SAME objects — no regeneration, no mutation.
        assert {id(t) for t in service._navigator.pool} == pool_ids
        assert {id(t) for t in service._navigator.history} == history_ids
        assert len(service._navigator.pool) == 2

    def test_move_shuffle_history_unchanged(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)
        service.next()
        picked = fake_audio.loaded
        fake_audio.trigger_media_accepted(picked)  # history = [a, picked]
        history_ids = {id(t) for t in service._navigator.history}
        service.move(1, 2)
        assert {id(t) for t in service._navigator.history} == history_ids

    def test_move_previous_follows_real_history(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)
        service.next()
        picked = fake_audio.loaded
        fake_audio.trigger_media_accepted(picked)
        service.previous()  # walk history back to a
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0
        loaded_before = fake_audio.loaded
        service.move(2, 0)  # [c, a, b] — the current a relocates to index 1
        assert service.state.current_track.file_path == a  # identity preserved
        service.previous()
        # Real history holds only [a]: previous() must NOT fabricate an
        # index-artifact target (index_of(a) - 1 == 0 → c). No load occurs.
        assert fake_audio.loaded == loaded_before
        assert service.state.current_track.file_path == a


class TestNavigationTruthfulness:
    """M4 Original Closeout: QueueService owns the truthful navigation values.

    Contract under test (NOT yet implemented in production):
    - `has_next`: shuffle ON → bool(pool) or repeat_mode != NONE; shuffle
      OFF + ALL → True whenever non-empty (manual Next wraps); shuffle OFF +
      NONE → current_index + 1 < len(tracks).
    - `has_previous` (NEW property): shuffle ON → len(navigator.history) >= 2
      (previous_pick requires REAL history of at least two entries — the
      current entry never counts as a previous step); shuffle OFF + ALL →
      True whenever non-empty (manual Previous at first wraps to last);
      shuffle OFF + NONE → current_index > 0.
    - Manual navigation ignores Repeat ONE (never trapped): `next()` is the
      shuffle pool pick, or natural-order (ALL → wrap, NONE → current + 1;
      at last with NONE → deterministic no-op); `previous()` is the
      navigator history walk, or natural-order (ALL → wrap, NONE →
      current - 1; at first with NONE → deterministic no-op).
    """

    def _shuffle_queue(self, playback_service, seed: int = 42):
        from michi.application.queue_service import QueueService

        return QueueService(playback_service, rng=random.Random(seed))

    def test_has_previous_shuffle_uses_history(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # history = [a]
        assert service.has_previous is False  # len(history) < 2
        service.next()
        picked = fake_audio.loaded
        fake_audio.trigger_media_accepted(picked)  # history = [a, picked]
        assert service.has_previous is True

    def test_has_next_shuffle_uses_pool(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)
        assert service.has_next is True  # pool non-empty
        for _ in range(2):  # consume the pool
            service.next()
            fake_audio.trigger_media_accepted(fake_audio.loaded)
        assert service.has_next is False  # pool empty, repeat NONE
        service.set_repeat_mode(RepeatMode.ALL)
        assert service.has_next is True  # repeat ALL → cycle continues

    def test_repeat_one_eom_replays_current(self, playback_service, fake_audio):
        """Pin at the navigation level: ONE + shuffle + non-empty pool → EOM
        replays the current entry (existing precedence) and has_next stays
        True (the pool is still non-empty — the UI may truthfully claim more
        music is available)."""
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            service.add(p)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b, c}
        service.set_repeat_mode(RepeatMode.ONE)
        fake_audio.trigger_end_of_media()
        assert fake_audio.loaded == a  # current replays, NOT a pool pick
        assert service.has_next is True  # pool still non-empty
        fake_audio.trigger_media_accepted(a)
        assert service.state.current_index == 0

    def test_repeat_one_manual_next_navigates(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        queue_service.set_repeat_mode(RepeatMode.ONE)
        queue_service.next()  # manual Next is NOT trapped by ONE
        assert fake_audio.loaded == b
        fake_audio.trigger_media_accepted(b)
        assert queue_service.state.current_index == 1

    def test_repeat_one_manual_previous_navigates(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(b)
        queue_service.set_repeat_mode(RepeatMode.ONE)
        queue_service.previous()  # manual Previous is NOT trapped by ONE
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert queue_service.state.current_index == 0

    def test_repeat_all_natural_wrap(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.set_repeat_mode(RepeatMode.ALL)
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(c)
        fake_audio.trigger_end_of_media()  # (2+1) % 3 == 0 → wraps
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert queue_service.state.current_index == 0

    def test_repeat_all_manual_next_wrap(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.set_repeat_mode(RepeatMode.ALL)
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(c)
        queue_service.next()  # manual Next at last with ALL → wraps to first
        assert fake_audio.loaded == a
        fake_audio.trigger_media_accepted(a)
        assert queue_service.state.current_index == 0

    def test_repeat_all_manual_previous_wrap(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.set_repeat_mode(RepeatMode.ALL)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        queue_service.previous()  # manual Previous at first with ALL → wraps to last
        assert fake_audio.loaded == c
        fake_audio.trigger_media_accepted(c)
        assert queue_service.state.current_index == 2

    def test_repeat_none_end_stops(self, queue_service, playback_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(c)
        fake_audio.trigger_end_of_media()  # NONE at last → stop
        assert fake_audio.state == "stopped"
        assert playback_service.state.status == PlaybackStatus.STOPPED
        assert queue_service.state.current_index == 2

    def test_has_next_truthful_at_last(self, queue_service, fake_audio):
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        for p in (a, b, c):
            queue_service.add(p)
        queue_service.play_index(2)
        fake_audio.trigger_media_accepted(c)
        assert queue_service.has_next is False  # NONE at last
        queue_service.set_repeat_mode(RepeatMode.ALL)
        assert queue_service.has_next is True  # ALL at last (manual wrap)
        queue_service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        assert queue_service.has_previous is True  # ALL at first (manual wrap)
        queue_service.set_repeat_mode(RepeatMode.NONE)
        assert queue_service.has_previous is False  # NONE at first


class TestEmptyQueueSemantics:
    """M4 Original Closeout: navigation on an empty queue is a deterministic
    no-op — no crash, no backend load, no state change, no notification."""

    def _assert_noop(self, queue_service, fake_audio, action) -> None:
        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        action()
        assert fake_audio.loaded is None  # no backend load
        assert queue_service.state.count == 0  # queue unchanged
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None
        assert calls == []  # ZERO notification

    def test_empty_next_noop(self, queue_service, fake_audio):
        self._assert_noop(queue_service, fake_audio, queue_service.next)

    def test_empty_previous_noop(self, queue_service, fake_audio):
        self._assert_noop(queue_service, fake_audio, queue_service.previous)

    def test_empty_play_current_noop(self, queue_service, fake_audio):
        self._assert_noop(queue_service, fake_audio, queue_service.play_current)


class TestQueueCapacity:
    """M4 Original Closeout: configurable queue capacity.

    Contract under test (NOT yet implemented in production):
    - `QueueService(playback_service, rng=None, max_tracks=10000)` — capacity
      configurable with a safe high default;
    - `add()` when count == max_tracks raises `QueueCapacityError`
      (michi.domain.queue) and leaves the queue unchanged — tracks, current,
      pending, and shuffle state untouched; NO silent truncation.
    """

    def _capacity_service(self, playback_service, max_tracks):
        from michi.application.queue_service import QueueService

        return QueueService(playback_service, max_tracks=max_tracks)

    def test_capacity_exact_boundary(self, playback_service):
        from michi.domain.queue import QueueCapacityError  # RED: undefined

        service = self._capacity_service(playback_service, 3)
        a, b, c, d = (
            Path("/tmp/a.mp3"),
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
            Path("/tmp/d.mp3"),
        )
        for p in (a, b, c):
            service.add(p)
        assert service.state.count == 3  # boundary fits
        with pytest.raises(QueueCapacityError):
            service.add(d)  # 4th entry exceeds capacity
        assert service.state.count == 3  # no silent truncation

    def test_over_capacity_state_unchanged(self, playback_service, fake_audio):
        from michi.domain.queue import QueueCapacityError  # RED: undefined

        service = self._capacity_service(playback_service, 2)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        service.add(a)
        service.add(b)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)  # current committed
        service.set_shuffle_enabled(True)  # shuffle state active
        with pytest.raises(QueueCapacityError):
            service.add(c)
        # The queue is untouched in every dimension.
        assert [t.file_path for t in service.state.tracks] == [a, b]  # tracks
        assert service.state.count == 2
        assert service.state.current_index == 0  # current unchanged
        assert service.state.current_track.file_path == a
        assert service._pending_track is None  # pending unchanged
        assert service.state.shuffle_enabled is True  # shuffle unchanged
        assert [t.file_path for t in service._navigator.pool] == [b]  # pool intact

    def test_capacity_default_high(self, playback_service):
        from michi.application.queue_service import QueueService

        service = QueueService(playback_service)
        assert service.max_tracks == 10000  # public read-only property


class TestM4FinalCorrections:
    """M4-FINAL-CORRECTION (RED — target contract NOT yet implemented):

    - `remove(committed current)`: `current_index` becomes -1 — NO fictitious
      current pointing at a track that never played; playback is NOT stopped
      (the removed track keeps playing until its natural end); a subsequent
      EOM does NOT auto-advance (index -1 → no-op); pending semantics
      unchanged (remove pending → stop + clear, TD-015); remove before
      current → shift (current_index -= 1, identity preserved).
    - shuffle + repeat ONE + exhausted pool + MANUAL Next: manual Next is a
      NO-OP (must NOT replay the current entry — the ONE replay rule is
      EOM-only); `has_next` with pool empty + ONE → False; with pool empty +
      ALL → True (regeneration); pool non-empty → True (any mode).
    - `QueueService(max_tracks <= 0)` → ValueError; `max_tracks` default
      10000 (existing); capacity behavior unchanged.
    - (internal) `_index_of_track` removed — `move` reuses `_index_of`
      (identity scan); existing move tests cover the behavior.
    """

    def _shuffle_queue(self, playback_service, seed: int = 42):
        from michi.application.queue_service import QueueService

        return QueueService(playback_service, rng=random.Random(seed))

    def test_remove_current_no_fictitious_current(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        assert queue_service.state.current_index == 1  # b committed

        calls = []
        queue_service.subscribe_changed(lambda: calls.append(1))
        queue_service.remove(1)  # the committed current itself

        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/tmp/a.mp3"),
            Path("/tmp/c.mp3"),
        ]
        # NO fictitious current: index -1, never a pointer to c (which never
        # played). The min-clamp behavior is the bug this test encodes.
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None
        # Playback is NOT stopped by the removal — the removed track keeps
        # playing until its natural end.
        assert fake_audio.state == "playing"
        assert calls == [1]  # ONE notification

    def test_remove_current_then_eom_no_advance(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        loaded_before = fake_audio.loaded
        queue_service.remove(1)  # current removed → index -1

        fake_audio.trigger_end_of_media()
        # No advance to a/c: nothing new is loaded (index -1 → no-op).
        assert fake_audio.loaded == loaded_before
        # The queue EOM no-ops at index -1 — never stops playback; the
        # removed track keeps playing (the contract is no-advance, not
        # queue-initiated stop).
        assert fake_audio.state == "playing"
        # The queue never re-points at a track that did not play.
        assert queue_service.state.current_index == -1
        assert queue_service.state.current_track is None

    def test_remove_track_before_current_shifts(self, queue_service, fake_audio):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.add(Path("/tmp/c.mp3"))
        queue_service.play_index(1)
        fake_audio.trigger_media_accepted(Path("/tmp/b.mp3"))
        b_track = queue_service.state.tracks[1]
        assert queue_service.state.current_index == 1

        queue_service.remove(0)  # a removed → b shifts to index 0

        assert [t.file_path for t in queue_service.state.tracks] == [
            Path("/tmp/b.mp3"),
            Path("/tmp/c.mp3"),
        ]
        assert queue_service.state.current_index == 0  # shifted, not dropped
        assert queue_service.state.current_track is b_track  # identity preserved

    def test_shuffle_one_exhausted_manual_next_noop(
        self, playback_service, fake_audio, monkeypatch
    ):
        service = self._shuffle_queue(playback_service)
        a, b = Path("/tmp/a.mp3"), Path("/tmp/b.mp3")
        service.add(a)
        service.add(b)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b}
        service.set_repeat_mode(RepeatMode.ONE)

        service.next()  # manual Next picks from the pool
        assert fake_audio.loaded == b
        fake_audio.trigger_media_accepted(b)
        assert service.state.current_index == 1  # b committed
        assert service.state.shuffle_enabled is True

        # Pool exhausted: manual Next must be a NO-OP — the ONE replay rule
        # is EOM-only and must NOT trap manual navigation into replaying the
        # current entry.
        calls = []
        orig = playback_service.load_and_play

        def spy(path, **kwargs):
            calls.append(path)
            orig(path, **kwargs)

        monkeypatch.setattr(playback_service, "load_and_play", spy)
        service.next()

        assert calls == []  # no new playback request
        assert fake_audio.loaded == b  # nothing reloaded
        assert service.state.current_index == 1  # no fake advance

    def test_shuffle_one_exhausted_has_next_false(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b = Path("/tmp/a.mp3"), Path("/tmp/b.mp3")
        service.add(a)
        service.add(b)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b}
        service.set_repeat_mode(RepeatMode.ONE)
        assert service.has_next is True  # pool non-empty

        service.next()
        fake_audio.trigger_media_accepted(fake_audio.loaded)  # pool now empty
        # ONE + exhausted pool: nothing remains — has_next must be False.
        assert service.has_next is False

    def test_shuffle_one_pool_nonempty_has_next_true(
        self, playback_service, fake_audio
    ):
        """Existing pin kept as regression: a non-empty pool under ONE means
        more music is available."""
        service = self._shuffle_queue(playback_service)
        a, b, c = Path("/tmp/a.mp3"), Path("/tmp/b.mp3"), Path("/tmp/c.mp3")
        service.add(a)
        service.add(b)
        service.add(c)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b, c} — non-empty
        service.set_repeat_mode(RepeatMode.ONE)
        assert service.has_next is True

    def test_shuffle_all_exhausted_has_next_true(self, playback_service, fake_audio):
        service = self._shuffle_queue(playback_service)
        a, b = Path("/tmp/a.mp3"), Path("/tmp/b.mp3")
        service.add(a)
        service.add(b)
        service.play_index(0)
        fake_audio.trigger_media_accepted(a)
        service.set_shuffle_enabled(True)  # pool = {b}
        service.set_repeat_mode(RepeatMode.ALL)

        service.next()
        fake_audio.trigger_media_accepted(fake_audio.loaded)  # pool now empty
        # ALL + exhausted pool: the cycle regenerates — more music remains.
        assert service.has_next is True

    def test_max_tracks_validation(self, playback_service):
        from michi.application.queue_service import QueueService
        from michi.domain.queue import QueueCapacityError

        with pytest.raises(ValueError):
            QueueService(playback_service, max_tracks=0)
        with pytest.raises(ValueError):
            QueueService(playback_service, max_tracks=-5)

        # Positive capacity constructs fine and enforces its boundary.
        service = QueueService(playback_service, max_tracks=1)
        assert service.max_tracks == 1
        service.add(Path("/tmp/a.mp3"))
        assert service.state.count == 1  # add works at capacity 1
        with pytest.raises(QueueCapacityError):
            service.add(Path("/tmp/b.mp3"))
        assert service.state.count == 1
