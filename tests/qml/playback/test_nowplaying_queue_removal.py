"""Verify NowPlayingBridge no longer exposes queue state after convergence."""

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

pytestmark = [pytest.mark.qml_module("playback")]


@pytest.fixture
def player():
    service = MagicMock()
    service.current = None
    service.state = "stopped"
    service.duration = 0
    return service


def test_nowplaying_bridge_does_not_observe_or_project_queue(
    player, audio_quality_adapter
):
    queue_service = QueueService(player_service=player)
    queue_service.subscribe = MagicMock(wraps=queue_service.subscribe)

    bridge = NowPlayingBridge(
        player_service=player,
        queue_service=queue_service,
        audio_quality_adapter=audio_quality_adapter,
    )

    queue_service.subscribe.assert_not_called()
    assert not hasattr(bridge, "queue")
    assert not hasattr(bridge, "queueChanged")
    assert not hasattr(bridge, "_queue")
    assert not hasattr(bridge, "_queue_internal_refs")
    assert not hasattr(bridge, "_normalize_queue")
    assert not hasattr(bridge, "_normalize_queue_item")
    assert not hasattr(bridge, "_unsubscribe_queue")


def test_nowplaying_bridge_retains_transport_without_queue_projection(
    player, audio_quality_adapter
):
    bridge = NowPlayingBridge(
        player_service=player,
        audio_quality_adapter=audio_quality_adapter,
    )

    result = bridge.togglePlay()

    assert result["ok"] is True
    player.play_or_resume.assert_called_once_with()
    assert not hasattr(bridge, "queue")


def test_nowplaying_bridge_retains_history_without_queue_projection(
    player, audio_quality_adapter
):
    bridge = NowPlayingBridge(
        player_service=player,
        audio_quality_adapter=audio_quality_adapter,
    )

    bridge._on_track("Song", "Artist", "Album")

    assert len(bridge.history) == 1
    assert bridge.history[0]["title"] == "Song"
    assert bridge.history[0]["artist"] == "Artist"
    assert not hasattr(bridge, "queue")
