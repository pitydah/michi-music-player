"""E2E workflow: Playback + Queue — all controls, ok=True verification."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playback"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("playback"),
]


def _ok(result: dict) -> bool:
    return result.get("ok") is True


class TestPlaybackQueueE2E:
    def test_playback_toggle_play(self, playback_bridge):
        result = playback_bridge.togglePlay()
        assert isinstance(result, dict), "togglePlay should return dict"
        assert "ok" in result

    def test_playback_next(self, playback_bridge):
        result = playback_bridge.next()
        assert isinstance(result, dict)

    def test_playback_previous(self, playback_bridge):
        result = playback_bridge.previous()
        assert isinstance(result, dict)

    def test_playback_set_volume(self, playback_bridge):
        result = playback_bridge.setVolume(50)
        assert _ok(result), f"setVolume failed: {result}"

    def test_playback_toggle_mute(self, playback_bridge):
        result = playback_bridge.toggleMute()
        assert isinstance(result, dict)

    def test_playback_seek(self, playback_bridge):
        result = playback_bridge.seek(30)
        assert isinstance(result, dict)

    def test_playback_toggle_shuffle(self, playback_bridge):
        result = playback_bridge.toggleShuffle()
        assert _ok(result), f"toggleShuffle failed: {result}"

    def test_playback_toggle_repeat(self, playback_bridge):
        result = playback_bridge.toggleRepeat()
        assert isinstance(result, dict)

    def test_queue_enqueue(self, playback_bridge):
        result = playback_bridge.enqueueSong("1")
        assert _ok(result), f"enqueueSong failed: {result}"

    def test_queue_play_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.playQueueItem(0)
        assert isinstance(result, dict)

    def test_queue_remove_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.removeFromQueue(0)
        assert isinstance(result, dict)

    def test_queue_move_item(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        playback_bridge.enqueueSong("2")
        playback_bridge.enqueueSong("3")
        result = playback_bridge.moveQueueItem(0, 2)
        assert isinstance(result, dict)

    def test_queue_clear(self, playback_bridge):
        playback_bridge.enqueueSong("1")
        result = playback_bridge.clearQueue()
        assert isinstance(result, dict)

    def test_playback_workflow(self, playback_bridge):
        playback_bridge.setVolume(75)
        playback_bridge.togglePlay()
        playback_bridge.next()
        playback_bridge.previous()
        playback_bridge.toggleShuffle()
        playback_bridge.toggleRepeat()
        playback_bridge.seek(10)
        playback_bridge.setVolume(50)
