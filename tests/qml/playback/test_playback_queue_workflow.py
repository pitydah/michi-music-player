"""Test playback-queue workflow: Library click QueueService PlayerService.

QueueService owns state; PlayerService executes; NowPlayingBridge reflects
PlayerService (no duplicate state); QueueBridge adapts QueueService.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


@pytest.fixture
def queue_service():
    return QueueService()


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue.return_value = []
    player.current = None
    player.state = "stopped"
    player.duration = 0
    player.get_track_by_id.return_value = None
    return player


@pytest.fixture
def queue_bridge(queue_service, mock_player):
    return QueueBridge(queue_service=queue_service, player_service=mock_player)


@pytest.fixture
def nowplaying_bridge(mock_player):
    return NowPlayingBridge(player_service=mock_player)


def test_library_add_to_queue_via_queue_service(queue_service, mock_player):
    track = {"track_id": 1, "title": "Song", "artist": "Artist",
             "album": "Album", "source_type": "local_file", "duration": 200}
    queue_service.add(track)
    assert queue_service.count == 1
    assert queue_service.get_current()["track_id"] == 1


def test_queue_service_add_syncs_to_player(queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    queue_service = QueueService(player_service=mock_player)
    track = {"track_id": 1, "title": "Song", "artist": "Artist"}
    queue_service.add(track)
    assert queue_service.count == 1
    mock_player.set_queue.assert_called_once()


def test_nowplaying_bridge_has_no_duplicate_control_logic(nowplaying_bridge):
    assert nowplaying_bridge is not None
    assert hasattr(nowplaying_bridge, 'queue')
    assert hasattr(nowplaying_bridge, 'history')


def test_nowplaying_bridge_queue_reads_from_player(mock_player, nowplaying_bridge):
    mock_player.get_queue.return_value = [
        {"track_id": 1, "title": "A", "artist": "X", "album": "Al",
         "source_type": "local_file", "duration": 200},
    ]
    nowplaying_bridge._on_queue(mock_player.get_queue.return_value)
    q = nowplaying_bridge.queue
    assert len(q) > 0
    assert q[0]["title"] == "A"


def test_queue_bridge_remove_uses_queue_service(queue_bridge, queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    queue_service.add({"track_id": 1, "title": "A"})
    queue_service.add({"track_id": 2, "title": "B"})
    result = queue_bridge.removeFromQueue(0)
    assert result["ok"]
    assert queue_service.count == 1
    assert queue_service.items[0]["track_id"] == 2


def test_queue_bridge_clear_uses_queue_service(queue_bridge, queue_service):
    queue_service.add({"track_id": 1, "title": "A"})
    queue_service.add({"track_id": 2, "title": "B"})
    result = queue_bridge.clearQueue()
    assert result["ok"]
    assert queue_service.count == 0


def test_full_workflow_library_to_playback(queue_service, mock_player):
    mock_player.set_queue = MagicMock()
    mock_player.play_index = MagicMock()

    tracks = [
        {"track_id": i, "title": f"Song {i}", "artist": "Artist",
         "source_type": "local_file", "duration": 200}
        for i in range(3)
    ]
    for t in tracks:
        queue_service.add(t)
    queue_service.current_index = 1

    mock_player.set_queue(queue_service.items)
    mock_player.get_queue.return_value = queue_service.items

    bridge = QueueBridge(queue_service=queue_service, player_service=mock_player)
    result = bridge.playFromIndex(1)
    assert result["ok"]
    mock_player.play_index.assert_called_with(1)


def test_queue_service_persistence_roundtrip(queue_service):
    tracks = [
        {"track_id": f"{i}", "track_uid": f"u{i}", "title": f"S{i}",
         "artist": "A", "source_type": "local_file", "duration": 200}
        for i in range(2)
    ]
    for t in tracks:
        queue_service.add(t)
    queue_service.save_state()

    fresh = QueueService()
    resolve_fn = MagicMock(side_effect=lambda item: item)
    result = fresh.load_state(resolve_fn=resolve_fn)
    assert result["ok"]
    assert fresh.count == 2


def _queue_state_path():
    from core.queue_service import _queue_state_path as qsp
import pytest
pytestmark = [pytest.mark.qml_module("playback")]

    return qsp()
