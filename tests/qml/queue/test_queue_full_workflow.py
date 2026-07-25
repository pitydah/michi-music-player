from __future__ import annotations
"""Test full queue workflow via QueueBridge and QueueListModel.
Covers: play from index, remove, reorder, clear, append, insert next,
save as playlist, undo preparation, multiple selection.
"""

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


@pytest.fixture
def queue_service():
    return QueueService()


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue = MagicMock(return_value=[
        {"id": 1, "track_uid": "uid1", "title": "Track 1", "artist": "A",
         "album": "Al", "duration": 200, "filepath": "/p1.flac", "source_type": "local_file"},
        {"id": 2, "track_uid": "uid2", "title": "Track 2", "artist": "B",
         "album": "Bl", "duration": 300, "filepath": "/p2.flac", "source_type": "local_file"},
        {"id": 3, "track_uid": "uid3", "title": "Track 3", "artist": "C",
         "album": "Cl", "duration": 250, "filepath": "/p3.flac", "source_type": "local_file"},
    ])
    player.play_index = MagicMock()
    player.remove_from_queue = MagicMock()
    player.move_in_queue = MagicMock()
    player.clear_queue = MagicMock()
    player.enqueue = MagicMock()
    return player


def test_queue_bridge_play_from_index(mock_player):
    service = QueueService(player_service=mock_player)
    service.set_items(mock_player.get_queue())
    bridge = QueueBridge(player_service=mock_player, queue_service=service)
    result = bridge.playFromIndex(1)
    assert result["ok"]
    assert service.current_index == 1
    mock_player.play.assert_called_once()
    mock_player.play_index.assert_not_called()


def test_queue_bridge_play_invalid_index(mock_player):
    service = QueueService(player_service=mock_player)
    service.set_items(mock_player.get_queue())
    bridge = QueueBridge(player_service=mock_player, queue_service=service)
    result = bridge.playFromIndex(99)
    assert not result["ok"]
    assert result["error"] == "INVALID_INDEX"


def test_queue_bridge_remove_from_queue(queue_service, mock_player):
    bridge = QueueBridge(player_service=mock_player, queue_service=queue_service)
    queue_service.add({"id": 1, "title": "T1"})
    queue_service.add({"id": 2, "title": "T2"})
    result = bridge.removeFromQueue(0)
    assert result["ok"]
    assert queue_service.count == 1


def test_queue_bridge_move_item(queue_service, mock_player):
    bridge = QueueBridge(player_service=mock_player, queue_service=queue_service)
    queue_service.add({"id": 1, "title": "T1"})
    queue_service.add({"id": 2, "title": "T2"})
    queue_service.add({"id": 3, "title": "T3"})
    result = bridge.moveItem(0, 2)
    assert result["ok"]
    assert queue_service.items[2]["title"] == "T1"


def test_queue_bridge_clear_queue(queue_service, mock_player):
    bridge = QueueBridge(player_service=mock_player, queue_service=queue_service)
    queue_service.add({"id": 1, "title": "T1"})
    result = bridge.clearQueue()
    assert result["ok"]
    assert queue_service.count == 0


def test_queue_bridge_empty_queue(mock_player):
    bridge = QueueBridge(
        player_service=mock_player,
        queue_service=QueueService(player_service=mock_player),
    )
    result = bridge.playFromIndex(0)
    assert not result["ok"]


def test_queue_bridge_no_player():
    with pytest.raises(AssertionError, match="queue_service is REQUIRED"):
        QueueBridge()


def test_queue_bridge_save_as_playlist_no_name(mock_player):
    from unittest.mock import MagicMock
    mock_pb = MagicMock()
    bridge = QueueBridge(
        player_service=mock_player,
        playlists_bridge=mock_pb,
        queue_service=QueueService(),
    )
    result = bridge.saveAsPlaylist("")
    assert not result["ok"]
    assert result["error"] == "EMPTY_NAME"


def test_queue_bridge_save_as_playlist(mock_player):
    from unittest.mock import MagicMock

    mock_pb = MagicMock()
    mock_pb.saveQueueAsPlaylist.return_value = {"ok": True}
    service = QueueService()
    service.set_items(mock_player.get_queue())
    bridge = QueueBridge(
        player_service=mock_player,
        playlists_bridge=mock_pb,
        queue_service=service,
    )
    result = bridge.saveAsPlaylist("My Queue")
    assert result["ok"]


def test_queue_bridge_refresh_updates_data(mock_player):
    service = QueueService()
    service.set_items(mock_player.get_queue())
    bridge = QueueBridge(player_service=mock_player, queue_service=service)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 3


def test_queue_bridge_remove_index(queue_service, mock_player):
    bridge = QueueBridge(player_service=mock_player, queue_service=queue_service)
    queue_service.add({"id": 1, "title": "T1"})
    result = bridge.removeFromQueue(0)
    assert result["ok"]


def test_queue_bridge_rejects_invalid_mutation_indices(queue_service, mock_player):
    bridge = QueueBridge(player_service=mock_player, queue_service=queue_service)
    queue_service.add({"id": 1, "title": "T1"})

    remove_result = bridge.removeFromQueue(2)
    move_result = bridge.moveItem(0, 2)

    assert not remove_result["ok"]
    assert remove_result["error"] == "INVALID_INDEX"
    assert not move_result["ok"]
    assert move_result["error"] == "INVALID_INDEX"
    assert queue_service.count == 1
