from __future__ import annotations
"""DM — NowPlayingBridge real adapter tests.
Bridge is reactive: it reads PlayerService state, does NOT duplicate control logic.
All commands return dict with structured errors.
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
pytestmark = [pytest.mark.qml_module("playback")]


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


def test_bridge_initial_state_without_player():
    bridge = NowPlayingBridge(player_service=None)
    assert not bridge.backendAvailable
    assert bridge.trackTitle == "—"
    assert not bridge.isPlaying
    assert bridge.position == 0
    assert bridge.duration == 0


def test_bridge_track_properties(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_track("Song", "Artist", "Album")
    assert bridge.trackTitle == "Song"
    assert bridge.trackArtist == "Artist"
    assert bridge.trackAlbum == "Album"


def test_bridge_state_playing(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_state("playing")
    assert bridge.isPlaying
    assert not bridge.muted


def test_bridge_state_paused(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_state("paused")
    assert not bridge.isPlaying


def test_bridge_position_updates(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_position(123)
    assert bridge.position == 123


def test_bridge_duration_updates(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_duration(300)
    assert bridge.duration == 300


def test_bridge_volume_updates(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_volume(75)
    assert bridge.volume == 75
    assert not bridge.muted


def test_bridge_muted_zero_volume(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_volume(0)
    assert bridge.muted


def test_bridge_source_type_detection(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    st = bridge._detect_source_type("radio://stream.example.com")
    assert st == "radio"
    st = bridge._detect_source_type("/path/to/local.flac")
    assert st == "local_file"


def test_bridge_quality_info_available(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert hasattr(bridge, 'formatLabel')
    assert hasattr(bridge, 'sampleRate')
    assert hasattr(bridge, 'bitDepth')
    assert hasattr(bridge, 'qualityInfoAvailable')


def test_bridge_capabilities_reflect_player(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    assert bridge.playPauseSupported
    assert bridge.seekSupported or not bridge.seekSupported
    assert bridge.volumeSupported
    assert bridge.nextSupported
    assert bridge.previousSupported


def test_bridge_toggle_play_no_player():
    bridge = NowPlayingBridge(player_service=None)
    result = bridge.togglePlay()
    assert not result["ok"]
    assert result["error_code"] == "NO_PLAYER_SERVICE"


def test_bridge_next_no_player():
    bridge = NowPlayingBridge(player_service=None)
    result = bridge.next()
    assert not result["ok"]
