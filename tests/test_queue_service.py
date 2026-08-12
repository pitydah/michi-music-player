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
        assert playback_service.state.status == PlaybackStatus.PLAYING
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
        assert playback_service.state.status == PlaybackStatus.PLAYING
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

    def test_queue_mutation_during_pending_does_not_commit_wrong_index(
        self, queue_service, playback_service, fake_audio
    ):
        self._commit_a(queue_service, fake_audio)
        queue_service.play_index(2)  # C pending at index 2
        queue_service.remove(0)  # a removed → C now sits at index 1
        fake_audio.trigger_media_accepted(Path("/tmp/c.mp3"))
        # Queue guard: index 2 no longer points at C → no stale index commit.
        assert queue_service.state.current_index == 0  # remove() semantics
        # Playback stays honest: C was genuinely accepted as the current media.
        assert playback_service.state.file_path == Path("/tmp/c.mp3")
