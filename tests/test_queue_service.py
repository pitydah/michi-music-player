"""Tests for QueueService — sole authority over QueueState."""

from pathlib import Path


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
