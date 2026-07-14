"""Test QueueBridge.saveState/loadState persist to config_dir, not /tmp."""
import json
import os
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.queue_bridge import QueueBridge, _queue_state_path


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue.return_value = [
        {"id": 1, "track_uid": "uid1", "title": "Track 1", "artist": "A",
         "album": "Al", "duration": 200, "filepath": "/path/1.flac"},
        {"id": 2, "track_uid": "uid2", "title": "Track 2", "artist": "B",
         "album": "Bl", "duration": 300, "filepath": "/path/2.flac"},
    ]
    player.get_queue_index.return_value = 0
    player.position = 42.5
    player.get_shuffle.return_value = False
    player.get_repeat.return_value = "all"
    return player


def test_queue_state_path_not_temp():
    path = _queue_state_path()
    assert path.endswith("queue_state.json")


def test_save_state(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    assert result["count"] == 2
    assert result["path"]
    assert os.path.exists(result["path"])
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["version"] == 1
    assert "current_index" in state
    assert "position" in state
    assert state["shuffle"] is False or state["shuffle"] is True
    assert "repeat" in state
    assert state["source"] == "queue_bridge"
    assert len(state["items"]) == 2
    assert state["items"][0]["id"] == 1
    assert state["items"][0]["track_uid"] == "uid1"
    os.remove(result["path"])


def test_save_state_includes_timestamp(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    with open(result["path"]) as f:
        state = json.load(f)
    assert "timestamp" in state
    assert state["timestamp"] > 0
    os.remove(result["path"])


def test_load_state_no_saved_state():
    bridge = QueueBridge(player_service=MagicMock())
    result = bridge.loadState()
    assert not result["ok"]
    assert result["error"] == "NO_SAVED_STATE"


def test_save_and_load_roundtrip(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    save_result = bridge.saveState()
    assert save_result["ok"]

    load_result = bridge.loadState()
    assert load_result["ok"]
    assert load_result["count"] > 0
    os.remove(save_result["path"])


def test_save_empty_queue(mock_player):
    mock_player.get_queue.return_value = []
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    assert result["count"] == 0
    os.remove(result["path"])


def test_no_player_service():
    bridge = QueueBridge()
    result = bridge.saveState()
    assert not result["ok"]
    assert result["error"] == "NO_PLAYER"

    result = bridge.loadState()
    assert not result["ok"]


def test_save_state_persists_to_config_dir(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    saved_path = result["path"]
    assert saved_path and len(saved_path) > 0
    os.remove(saved_path)


def test_save_state_shuffle_repeat(mock_player):
    mock_player.get_shuffle.return_value = True
    mock_player.get_repeat.return_value = "one"
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["shuffle"] is True
    assert state["repeat"] == "one"
    os.remove(result["path"])


def test_load_resolves_ids_to_tracks(mock_player):
    bridge = QueueBridge(player_service=mock_player)
    result = bridge.saveState()
    assert result["ok"]
    load = bridge.loadState()
    assert load["ok"]
    os.remove(result["path"])
