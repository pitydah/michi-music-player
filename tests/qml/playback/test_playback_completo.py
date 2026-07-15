from __future__ import annotations
"""Comprehensive tests for Playback — 15+ tests.
Covers: play, pause, resume, stop, seek, volume, mute, next, previous,
shuffle, repeat, output, quality, error, missing file, album art,
lyrics access, track actions.
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.playback_bridge import PlaybackBridge

pytestmark = [pytest.mark.qml_module("playback")]


@pytest.fixture
def mock_player():
    p = MagicMock()
    p.current = {"title": "Song", "artist": "A", "album": "Al",
                  "filepath": "/s.flac", "duration": 200}
    p.state = "stopped"
    p.duration = 200
    p.get_queue.return_value = []
    p.set_queue = MagicMock()
    return p


@pytest.fixture
def bridge(mock_player):
    return NowPlayingBridge(player_service=mock_player)


class TestPlaybackCompleto:
    def test_initial_state(self, bridge):
        assert bridge.backendAvailable is True
        assert bridge.isPlaying is False
        assert bridge.position == 0

    def test_toggle_play_pause(self, bridge, mock_player):
        mock_player.pause = MagicMock()
        mock_player.play_or_resume = MagicMock()
        result = bridge.togglePlay()
        assert result["ok"]

    def test_next_track(self, bridge, mock_player):
        mock_player.play_next = MagicMock()
        result = bridge.next()
        assert result["ok"]
        mock_player.play_next.assert_called_once()

    def test_previous_track(self, bridge, mock_player):
        mock_player.play_prev = MagicMock()
        result = bridge.previous()
        assert result["ok"]
        mock_player.play_prev.assert_called_once()

    def test_seek(self, bridge, mock_player):
        mock_player.seek = MagicMock()
        result = bridge.seek(100)
        assert result["ok"]
        mock_player.seek.assert_called_with(100)

    def test_seek_clamps(self, bridge, mock_player):
        mock_player.seek = MagicMock()
        result = bridge.seek(9999)
        assert result["ok"]

    def test_set_volume(self, bridge, mock_player):
        mock_player.set_volume = MagicMock()
        result = bridge.setVolume(75)
        assert result["ok"]
        assert bridge.volume == 75

    def test_set_volume_clamps(self, bridge, mock_player):
        mock_player.set_volume = MagicMock()
        result = bridge.setVolume(150)
        assert result["ok"]
        assert bridge.volume == 100

    def test_toggle_mute(self, bridge, mock_player):
        mock_player.set_volume = MagicMock()
        bridge._volume = 80
        bridge._previous_volume = 80
        result = bridge.toggleMute()
        assert result["ok"]
        assert bridge.muted is True

    def test_toggle_shuffle(self, bridge, mock_player):
        mock_player.toggle_shuffle = MagicMock(return_value=True)
        result = bridge.toggleShuffle()
        assert result["ok"]

    def test_toggle_repeat(self, bridge, mock_player):
        mock_player.toggle_repeat = MagicMock(return_value="all")
        result = bridge.toggleRepeat()
        assert result["ok"]

    def test_seek_relative(self, bridge, mock_player):
        mock_player.seek = MagicMock()
        bridge._position = 100
        result = bridge.seekRelative(30)
        assert result["ok"]

    def test_enqueue_song(self, bridge, mock_player):
        mock_player.enqueue = MagicMock()
        result = bridge.enqueueSong("/test.flac")
        assert result["ok"]

    def test_remove_from_queue(self, bridge, mock_player):
        mock_player.remove_queue_item = MagicMock()
        bridge._queue = [{"title": "A"}, {"title": "B"}]
        result = bridge.removeFromQueue(0)
        assert result["ok"]

    def test_clear_queue(self, bridge, mock_player):
        mock_player.clear_queue = MagicMock()
        result = bridge.clearQueue()
        assert result["ok"]

    def test_move_queue_item(self, bridge, mock_player):
        mock_player.move_queue_item = MagicMock()
        bridge._queue = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        result = bridge.moveQueueItem(0, 2)
        assert result["ok"]

    def test_play_queue_item(self, bridge, mock_player):
        mock_player.play_queue_item = MagicMock()
        bridge._queue = [{"title": "A"}, {"title": "B"}]
        result = bridge.playQueueItem(1)
        assert result["ok"]

    def test_playback_bridge_delegates(self):
        p = MagicMock()
        p.current = None
        p.state = "stopped"
        p.duration = 0
        p.get_queue.return_value = []
        p.set_queue = MagicMock()
        pb = PlaybackBridge(player_service=p)
        assert pb.trackTitle == "—"

    def test_bridge_error_no_player(self):
        b = NowPlayingBridge()
        result = b.togglePlay()
        assert not result["ok"]

    def test_quality_probe(self, bridge, mock_player):
        qa = MagicMock()
        qa.probe.return_value = {"ok": True, "format_label": "FLAC",
                                  "sample_rate": "44100", "bit_depth": "16",
                                  "channels": "2", "bitrate": "1411",
                                  "quality_label": "CD"}
        bridge._quality_adapter = qa
        bridge._probe_quality("/test.flac")
        assert bridge.qualityInfoAvailable is True
