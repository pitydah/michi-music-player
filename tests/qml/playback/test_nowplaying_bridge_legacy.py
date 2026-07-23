"""DM — NowPlayingBridge real adapter tests.
Bridge is reactive: it reads PlayerService state, does NOT duplicate control logic.
All commands return dict with structured errors.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
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


@pytest.fixture
def queue_service(mock_player):
    return QueueService(player_service=mock_player)


@pytest.fixture
def bridge(mock_player, queue_service, audio_quality_adapter):
    return NowPlayingBridge(
        player_service=mock_player,
        queue_service=queue_service,
        audio_quality_adapter=audio_quality_adapter,
    )


@pytest.fixture
def bridge_without_player(mock_player, audio_quality_adapter):
    bridge = NowPlayingBridge(
        player_service=mock_player,
        audio_quality_adapter=audio_quality_adapter,
    )
    bridge._player = None
    bridge._backend_available = False
    bridge._playback_status = "unavailable"
    bridge._safe_mode = True
    return bridge


def test_bridge_initial_state_without_player(bridge_without_player):
    bridge = bridge_without_player
    assert not bridge.backendAvailable
    assert bridge.trackTitle == "—"
    assert not bridge.isPlaying
    assert bridge.position == 0
    assert bridge.duration == 0


def test_bridge_track_properties(bridge):
    bridge._on_track("Song", "Artist", "Album")
    assert bridge.trackTitle == "Song"
    assert bridge.trackArtist == "Artist"
    assert bridge.trackAlbum == "Album"


def test_bridge_state_playing(bridge):
    bridge._on_state("playing")
    assert bridge.isPlaying
    assert not bridge.muted


def test_bridge_state_paused(bridge):
    bridge._on_state("paused")
    assert not bridge.isPlaying


def test_bridge_position_updates(bridge):
    bridge._on_position(123)
    assert bridge.position == 123


def test_bridge_duration_updates(bridge):
    bridge._on_duration(300)
    assert bridge.duration == 300


def test_bridge_volume_updates(bridge):
    bridge._on_volume(75)
    assert bridge.volume == 75
    assert not bridge.muted


def test_bridge_muted_zero_volume(bridge):
    bridge._on_volume(0)
    assert bridge.muted


def test_bridge_source_type_detection(bridge):
    st = bridge._detect_source_type("radio://stream.example.com")
    assert st == "radio"
    st = bridge._detect_source_type("/path/to/local.flac")
    assert st == "local_file"


def test_bridge_quality_info_available(bridge):
    assert hasattr(bridge, 'formatLabel')
    assert hasattr(bridge, 'sampleRate')
    assert hasattr(bridge, 'bitDepth')
    assert hasattr(bridge, 'qualityInfoAvailable')


def test_bridge_capabilities_reflect_player(bridge):
    assert bridge.playPauseSupported
    assert isinstance(bridge.seekSupported, bool)
    assert bridge.volumeSupported
    assert bridge.nextSupported
    assert bridge.previousSupported
    assert not hasattr(bridge, "queue")


def test_bridge_toggle_play_no_player(bridge_without_player):
    bridge = bridge_without_player
    result = bridge.togglePlay()
    assert not result["ok"]
    assert result["error_code"] == "NO_PLAYER_SERVICE"


def test_bridge_next_no_player(bridge_without_player):
    bridge = bridge_without_player
    result = bridge.next()
    assert not result["ok"]
