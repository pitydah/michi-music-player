"""Tests for QueueService — sole authority over QueueState."""

from pathlib import Path

import pytest


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
        assert queue_service.state.current_index == 1
        assert fake_audio.state == "playing"

    def test_next(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(0)
        queue_service.next()
        assert queue_service.state.current_index == 1

    def test_next_at_end(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.play_index(0)
        queue_service.next()
        assert queue_service.state.current_index == 0  # stays

    def test_previous(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.add(Path("/tmp/b.mp3"))
        queue_service.play_index(1)
        queue_service.previous()
        assert queue_service.state.current_index == 0

    def test_previous_at_start(self, queue_service):
        queue_service.add(Path("/tmp/a.mp3"))
        queue_service.play_index(0)
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
        queue_service.next()
        queue_service.previous()

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

        assert queue_service.state.current_index == 1
        assert queue_service.state.current_track.file_path == Path("/tmp/b.mp3")
