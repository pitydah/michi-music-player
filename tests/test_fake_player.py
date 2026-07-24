"""Tests for FakePlayer — lightweight test backend."""
import pytest


@pytest.fixture
def player():
    from audio.fake_player import FakePlayer
    return FakePlayer(use_timer=False)


@pytest.fixture
def player_with_timer():
    from audio.fake_player import FakePlayer
    return FakePlayer(use_timer=True)


class TestFakePlayer:
    def test_initial_state(self, player):
        from audio.fake_player import PlaybackState
        assert player.state == PlaybackState.STOPPED
        assert player.position == 0.0
        assert player.duration == 0.0
        assert player.volume == 80

    def test_play(self, player):
        from audio.fake_player import PlaybackState
        player.play("/test/song.flac")
        assert player.state == PlaybackState.PLAYING
        assert player.current_filepath == "/test/song.flac"
        assert player.duration == 180.0

    def test_pause(self, player):
        from audio.fake_player import PlaybackState
        player.play("/test/song.flac")
        player.pause()
        assert player.state == PlaybackState.PAUSED

    def test_stop(self, player):
        from audio.fake_player import PlaybackState
        player.play("/test/song.flac")
        player.stop()
        assert player.state == PlaybackState.STOPPED
        assert player.position == 0.0

    def test_seek(self, player):
        player.play("/test/song.flac")
        player.seek(30.0)
        assert player.position == 30.0

    def test_volume(self, player):
        player.set_volume(50)
        assert player.volume == 50
        player.set_volume(200)
        assert player.volume == 100
        player.set_volume(-10)
        assert player.volume == 0

    def test_queue_operations(self, player):
        items = [{"filepath": "/test/a.flac"}, {"filepath": "/test/b.flac"}]
        player.set_queue(items)
        assert len(player.queue) == 2
        player.enqueue([{"filepath": "/test/c.flac"}])
        assert len(player.queue) == 3
        player.clear_queue()
        assert len(player.queue) == 0

    def test_next_previous(self, player):
        items = [{"filepath": "/test/a.flac"}, {"filepath": "/test/b.flac"}]
        player.set_queue(items)
        player.play("/test/a.flac")
        # play() doesn't set queue index — next/previous work from queue position
        player._current_index = 0
        player.next()
        assert player.current_filepath == "/test/b.flac"
        player.previous()
        assert player.current_filepath == "/test/a.flac"

    def test_repeat_all(self, player):
        from audio.fake_player import PlaybackState
        items = [{"filepath": "/test/a.flac"}]
        player.set_queue(items)
        player.set_repeat("all")
        player.play("/test/a.flac")
        player.next()
        assert player.state == PlaybackState.PLAYING  # loops back

    def test_error_mode(self, player):
        from audio.fake_player import PlaybackState
        player.set_error_mode(True)
        player.play("/test/song.flac")
        assert player.state == PlaybackState.FAILED
        assert player.last_error == "SIMULATED_ERROR"

    def test_mute(self, player):
        player.set_muted(True)
        assert player.muted
        player.set_muted(False)
        assert not player.muted

    def test_position_advances_with_timer(self, player_with_timer):
        p = player_with_timer
        p.play("/test/song.flac")
        p._advance_position()
        assert p.position > 0.0

    def test_finished_signal(self, player):
        results = []

        def on_finished():
            results.append("finished")

        player.finished.connect(on_finished)
        player.play("/test/short.flac")
        player._duration = 0.5
        player._advance_position()
        player._advance_position()
        player._advance_position()
        player._advance_position()
        player._advance_position()
        assert len(results) == 1

    def test_state_transitions(self, player):
        states = []

        def on_state(s):
            states.append(s)

        player.state_changed.connect(on_state)
        player.play("/test/song.flac")
        player.pause()
        player.resume()
        player.stop()
        assert len(states) >= 4
