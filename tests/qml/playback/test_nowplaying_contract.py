"""NowPlayingBridge contract tests — no local queue, delegation only."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

pytestmark = [pytest.mark.qml_module("queue")]


def _make_bridge(has_queue=True, has_player=True):
    player = MagicMock() if has_player else None
    queue = MagicMock() if has_queue else None
    quality = MagicMock()
    quality.probe.return_value = {"ok": False}
    return NowPlayingBridge(
        player_service=player,
        queue_service=queue,
        audio_quality_adapter=quality,
    )


class TestNoLocalQueue:
    """NowPlayingBridge must NOT maintain its own queue state."""

    def test_no_queue_list_attribute(self):
        bridge = _make_bridge()
        assert not hasattr(bridge, "_queue_list")
        assert not hasattr(bridge, "_items")

    def test_no_local_queue_index(self):
        bridge = _make_bridge()
        assert not hasattr(bridge, "_local_current_index")

    def test_next_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.next.return_value = {"ok": True}
        result = bridge.next()
        bridge._queue_service.next.assert_called_once()

    def test_previous_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.previous.return_value = {"ok": True}
        result = bridge.previous()
        bridge._queue_service.previous.assert_called_once()

    def test_toggle_shuffle_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.toggle_shuffle.return_value = {"ok": True}
        result = bridge.toggleShuffle()
        bridge._queue_service.toggle_shuffle.assert_called_once()

    def test_toggle_repeat_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.toggle_repeat.return_value = {"ok": True}
        result = bridge.toggleRepeat()
        bridge._queue_service.toggle_repeat.assert_called_once()

    def test_enqueue_song_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.enqueue.return_value = {"ok": True}
        result = bridge.enqueueSong("/path/to/song.mp3")
        bridge._queue_service.enqueue.assert_called_once()

    def test_remove_from_queue_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.remove.return_value = {"ok": True}
        bridge._queue_service.count = 5
        result = bridge.removeFromQueue(2)
        bridge._queue_service.remove.assert_called_once_with([2])

    def test_clear_queue_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.clear.return_value = {"ok": True}
        result = bridge.clearQueue()
        bridge._queue_service.clear.assert_called_once()

    def test_move_queue_item_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.reorder.return_value = {"ok": True}
        bridge._queue_service.count = 5
        result = bridge.moveQueueItem(1, 3)
        bridge._queue_service.reorder.assert_called_once_with(1, 3)

    def test_play_queue_item_delegates_to_queue_service(self):
        bridge = _make_bridge()
        bridge._queue_service.play_from_index.return_value = {"ok": True}
        bridge._queue_service.count = 5
        result = bridge.playQueueItem(2)
        bridge._queue_service.play_from_index.assert_called_once_with(2)

    def test_no_queue_returns_unsupported(self):
        bridge = _make_bridge(has_queue=False)
        result = bridge.next()
        assert result.get("ok") is False
        assert result.get("error_code") == "UNSUPPORTED"


class TestNowPlayingBridgeProperties:
    """Verify key properties exist and read from player_service."""

    def test_has_track_title(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "trackTitle")

    def test_has_is_playing(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "isPlaying")

    def test_has_position(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "position")

    def test_has_duration(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "duration")

    def test_has_volume(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "volume")

    def test_has_repeat_mode(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "repeatMode")

    def test_has_shuffle_enabled(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "shuffleEnabled")

    def test_has_command_pending(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "commandPending")

    def test_has_play_pause_supported(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "playPauseSupported")

    def test_has_seek_supported(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "seekSupported")

    def test_has_volume_supported(self):
        bridge = _make_bridge()
        assert hasattr(bridge, "volumeSupported")
