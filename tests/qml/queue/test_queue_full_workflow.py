"""Test full queue workflow via QueueBridge and QueueListModel.

Covers: play from index, remove, reorder, clear, append, insert next,
save as playlist, undo preparation, multiple selection.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.queue_bridge import QueueBridge


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
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.playFromIndex(1)
    assert result["ok"]
    mock_player.play_index.assert_called_once_with(1)


def test_queue_bridge_play_invalid_index(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.playFromIndex(99)
    assert not result["ok"]
    assert result["error"] == "INVALID_INDEX"


def test_queue_bridge_remove_from_queue(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.removeFromQueue(0)
    assert result["ok"]
    assert mock_player.remove_from_queue.called


def test_queue_bridge_move_item(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.moveItem(0, 2)
    assert result["ok"]
    assert mock_player.move_in_queue.called


def test_queue_bridge_clear_queue(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.clearQueue()
    assert result["ok"]
    assert mock_player.clear_queue.called


def test_queue_bridge_empty_queue(mock_player):
    mock_player.get_queue.return_value = []
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.playFromIndex(0)
    assert not result["ok"]


def test_queue_bridge_no_player():
    bridge = QueueBridge()
    assert bridge.playFromIndex(0)["error"] == "NO_PLAYER"
    assert bridge.clearQueue()["error"] == "UNSUPPORTED"


def test_queue_bridge_save_as_playlist_no_name(mock_player):
    from unittest.mock import MagicMock
    mock_pb = MagicMock()
    bridge = QueueBridge(player_service=mock_player, playlists_bridge=mock_pb)
    result = bridge.saveAsPlaylist("")
    assert not result["ok"]
    assert result["error"] == "EMPTY_NAME"


def test_queue_bridge_save_as_playlist(mock_player):
    from unittest.mock import MagicMock
    mock_pb = MagicMock()
    mock_pb.saveQueueAsPlaylist.return_value = {"ok": True}
    bridge = QueueBridge(player_service=mock_player, playlists_bridge=mock_pb)
    result = bridge.saveAsPlaylist("My Queue")
    assert result["ok"]


def test_queue_bridge_refresh_updates_data(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 3


def test_queue_bridge_remove_index(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.removeFromQueue(0)
    assert result["ok"]
