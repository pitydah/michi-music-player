"""Test error propagation through playback bridges.

Errors must propagate correctly: PlayerService → NowPlayingBridge → QML.
No falla silenciosa — if backend is unavailable, playback MUST NOT appear to start.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.playback_bridge import PlaybackBridge


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


def test_backend_unavailable_propagated(mock_player):
    mock_player.state = "stopped"
    bridge = NowPlayingBridge(player_service=None)
    assert not bridge.backendAvailable
    assert not bridge.hasTrack


def test_error_code_not_found_propagation():
    from ui_qml_bridge.nowplaying_bridge import _safe_message, _err
    msg = _safe_message("NOT_FOUND")
    assert msg == "Elemento no encontrado"
    result = _err("test", "NOT_FOUND")
    assert not result["ok"]
    assert result["error_code"] == "NOT_FOUND"


def test_error_emitted_on_playback_failure(mock_player):
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._on_error("PLAYBACK_ERROR")
    assert len(bridge.errorMessage) > 0


def test_queue_unavailable_error():
    from ui_qml_bridge.nowplaying_bridge import _err
    result = _err("enqueueSong", "QUEUE_UNAVAILABLE")
    assert not result["ok"]
    assert result["error_code"] == "QUEUE_UNAVAILABLE"


def test_invalid_position_error():
    from ui_qml_bridge.nowplaying_bridge import _safe_message
import pytest
pytestmark = [pytest.mark.qml_module("playback")]

    msg = _safe_message("INVALID_POSITION")
    assert msg == "Posición inválida"


def test_no_player_service_on_all_commands(mock_player):
    bridge = NowPlayingBridge(player_service=None)
    assert not bridge.togglePlay()["ok"]
    assert not bridge.next()["ok"]
    assert not bridge.previous()["ok"]
    assert not bridge.seek(0)["ok"]
    assert not bridge.setVolume(50)["ok"]


def test_playback_bridge_error_propagation(mock_player):
    np_bridge = NowPlayingBridge(player_service=mock_player)
    pb_bridge = PlaybackBridge(nowplaying_bridge=np_bridge)
    assert hasattr(pb_bridge, 'stateChanged')
    assert pb_bridge.backendAvailable is not None
