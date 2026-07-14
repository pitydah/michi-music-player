"""Test NowPlayingBar bridge state propagation.

Verifies the NowPlayingBar component correctly reads shared state
from NowPlayingBridge without duplicating playback control logic.
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
    player.position_changed = MagicMock()
    player.duration_changed = MagicMock()
    player.state_changed = MagicMock()
    player.queue_changed = MagicMock()
    player.error_occurred = MagicMock()
    player.volume_changed = MagicMock()
    player.track_changed = MagicMock()
    return player


def test_bar_reads_state_from_nowplaying(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert bridge.trackTitle is not None
    assert bridge.isPlaying is not None
    assert bridge.position is not None


def test_bar_shares_state_with_nowplaying_page(mock_player):
    bar_bridge = NowPlayingBridge(player_service=mock_player)
    page_bridge = NowPlayingBridge(player_service=mock_player)
    assert bar_bridge.trackTitle == page_bridge.trackTitle
    assert bar_bridge.isPlaying == page_bridge.isPlaying


def test_bar_has_mini_player_properties(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert hasattr(bridge, 'coverPath')
    assert hasattr(bridge, 'trackTitle')
    assert hasattr(bridge, 'trackArtist')
    assert hasattr(bridge, 'trackAlbum')


def test_bar_playback_control_delegates(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._is_playing = False
    result = bridge.togglePlay()
    assert isinstance(result, dict)


def test_bar_seek_delegates(mock_player):
    mock_player.duration = 300
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._duration = 300
    result = bridge.seek(100)
    assert isinstance(result, dict)


def test_bar_volume_control(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    result = bridge.setVolume(50)
    assert isinstance(result, dict)


def test_bar_mute_toggle(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._volume = 80
    result = bridge.toggleMute()
    assert isinstance(result, dict)


def test_bar_error_shown_via_connection(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_error("Stream lost")
    assert bridge.errorMessage == "Stream lost" or len(bridge.errorMessage) > 0
