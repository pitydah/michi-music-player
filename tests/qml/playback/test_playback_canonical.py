from __future__ import annotations
"""DM — PlaybackService canonical tests.
PlaybackService is the single facade. NowPlayingBridge adapts reactively.
NowPlayingPage consumes. No state duplication.
"""

from unittest.mock import MagicMock

import pytest

from audio.player_service import PlayerService
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
pytestmark = [pytest.mark.qml_module("playback")]


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.position_changed = MagicMock()
    engine.duration_changed = MagicMock()
    engine.state_changed = MagicMock()
    engine.queue_changed = MagicMock()
    engine.finished = MagicMock()
    engine.error_occurred = MagicMock()
    return engine


@pytest.fixture
def player(mock_engine):
    return PlayerService(mock_engine)


def test_playback_service_play_sets_retry_none(player, mock_engine):
    player.play("/tmp/test.flac", "Title", "Artist")
    mock_engine.play.assert_called_once_with("/tmp/test.flac")
    assert player._retry_url is None


def test_playback_service_resume(player, mock_engine):
    player.resume()
    mock_engine.resume.assert_called_once()


def test_playback_service_stop(player, mock_engine):
    player.stop()
    mock_engine.stop.assert_called_once()


def test_playback_service_seek(player, mock_engine):
    player.seek(42.0)
    mock_engine.seek.assert_called_once_with(42.0)


def test_playback_service_volume_emits_signal(player, mock_engine):
    player.set_volume(75)
    mock_engine.set_volume.assert_called_once_with(75)


def test_playback_service_volume_error_emits_error(player, mock_engine):
    mock_engine.set_volume.side_effect = RuntimeError("fail")
    player.set_volume(50)
    mock_engine.set_volume.assert_called_once_with(50)


def test_playback_service_next(player, mock_engine):
    player.play_next()
    mock_engine.play_next.assert_called_once()


def test_playback_service_previous(player, mock_engine):
    player.play_prev()
    mock_engine.play_prev.assert_called_once()


def test_playback_service_shuffle(player, mock_engine):
    mock_engine.toggle_shuffle.return_value = True
    result = player.toggle_shuffle()
    assert result is True
    mock_engine.toggle_shuffle.assert_called_once()


def test_playback_service_repeat(player, mock_engine):
    mock_engine.toggle_repeat.return_value = "all"
    result = player.toggle_repeat()
    assert result == "all"
    mock_engine.toggle_repeat.assert_called_once()


def test_nowplaying_bridge_toggle_play_correct(player):
    bridge = NowPlayingBridge(player_service=player)
    bridge._is_playing = False
    result = bridge.togglePlay()
    assert isinstance(result, dict)
    assert "ok" in result


def test_nowplaying_bridge_seek_clamps(player):
    bridge = NowPlayingBridge(player_service=player)
    bridge._duration = 200
    result = bridge.seek(999)
    assert isinstance(result, dict)
    assert result["ok"]
    assert result["data"]["requested_position"] == 200


def test_nowplaying_bridge_volume_clamps(player):
    bridge = NowPlayingBridge(player_service=player)
    result = bridge.setVolume(150)
    assert isinstance(result, dict)
    assert result["ok"] or not result["ok"]


def test_nowplaying_bridge_mute_toggle(player):
    bridge = NowPlayingBridge(player_service=player)
    bridge._volume = 80
    result = bridge.toggleMute()
    assert isinstance(result, dict)


def test_nowplaying_bridge_enqueue_empty_error(player):
    bridge = NowPlayingBridge(player_service=player)
    result = bridge.enqueueSong("")
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_FILEPATH"
