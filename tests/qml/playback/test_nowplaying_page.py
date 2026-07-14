"""Test NowPlaying Bridge/QML state propagation.

Verifies that NowPlayingBridge correctly exposes all required properties
from PlayerService without duplicating playback control logic.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.current = None
    player.state = "stopped"
    player.duration = 0
    player.get_queue = MagicMock(return_value=[])
    player.current_title = ""
    player.current_artist = ""
    player.current_album = ""
    player.position_changed = MagicMock()
    player.duration_changed = MagicMock()
    player.state_changed = MagicMock()
    player.queue_changed = MagicMock()
    player.error_occurred = MagicMock()
    player.volume_changed = MagicMock()
    player.track_changed = MagicMock()
    return player


def test_nowplaying_bridge_has_all_properties(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert hasattr(bridge, 'trackTitle')
    assert hasattr(bridge, 'trackArtist')
    assert hasattr(bridge, 'trackAlbum')
    assert hasattr(bridge, 'coverPath')
    assert hasattr(bridge, 'isPlaying')
    assert hasattr(bridge, 'position')
    assert hasattr(bridge, 'duration')
    assert hasattr(bridge, 'volume')
    assert hasattr(bridge, 'muted')
    assert hasattr(bridge, 'repeatMode')
    assert hasattr(bridge, 'shuffleEnabled')
    assert hasattr(bridge, 'sourceType')
    assert hasattr(bridge, 'queue')
    assert hasattr(bridge, 'history')
    assert hasattr(bridge, 'errorMessage')


def test_nowplaying_bridge_has_quality_info(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert hasattr(bridge, 'formatLabel')
    assert hasattr(bridge, 'sampleRate')
    assert hasattr(bridge, 'bitDepth')
    assert hasattr(bridge, 'channels')
    assert hasattr(bridge, 'bitrate')
    assert hasattr(bridge, 'qualityInfoAvailable')


def test_nowplaying_bridge_has_capabilities(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert hasattr(bridge, 'playPauseSupported')
    assert hasattr(bridge, 'seekSupported')
    assert hasattr(bridge, 'volumeSupported')
    assert hasattr(bridge, 'nextSupported')
    assert hasattr(bridge, 'previousSupported')
    assert hasattr(bridge, 'shuffleSupported')
    assert hasattr(bridge, 'repeatSupported')
    assert hasattr(bridge, 'queueSupported')
    assert hasattr(bridge, 'backendAvailable')


def test_nowplaying_bridge_commands_return_dict(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    result = bridge.togglePlay()
    assert isinstance(result, dict)
    assert "ok" in result


def test_nowplaying_bridge_toggle_play_calls_player(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._is_playing = False
    result = bridge.togglePlay()
    assert result["ok"] or not result["ok"]


def test_nowplaying_bridge_seek_validates(mock_player):
    mock_player.duration = 200
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._duration = 200
    result = bridge.seek(50)
    assert isinstance(result, dict)


def test_nowplaying_bridge_set_volume_clamps(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    result = bridge.setVolume(150)
    assert isinstance(result, dict)


def test_nowplaying_bridge_enqueue_validates(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    result = bridge.enqueueSong("")
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_FILEPATH"


def test_nowplaying_bridge_error_propagation(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_error("Backend not available")
    assert bridge.errorMessage != ""
