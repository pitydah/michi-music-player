"""Test QueueService persistence (save/load queue state)."""
import json
import os

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService, _queue_state_path


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.get_queue = MagicMock(return_value=[
        {"id": 1, "track_uid": "uid1", "title": "Track 1", "artist": "A",
         "album": "Al", "duration": 200, "filepath": "/path/1.flac", "source_type": "local_file"},
        {"id": 2, "track_uid": "uid2", "title": "Track 2", "artist": "B",
         "album": "Bl", "duration": 300, "filepath": "/path/2.flac", "source_type": "local_file"},
    ])
    return player


def test_queue_state_path_not_temp():
    path = _queue_state_path()
    assert path.endswith("queue_state.json")


def test_save_state(mock_player):
    svc = QueueService(player_service=mock_player)
    result = svc.save_state()
    assert result["ok"]
    assert result["count"] == 2
    assert os.path.exists(result["path"])
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["version"] == 1
    assert "timestamp" in state
    assert len(state["items"]) == 2
    os.remove(result["path"])


def test_save_state_empty_queue(mock_player):
    mock_player.get_queue.return_value = []
    svc = QueueService(player_service=mock_player)
    result = svc.save_state()
    assert result["ok"]
    assert result["count"] == 0
    os.remove(result["path"])


def test_load_state_no_saved_state(mock_player):
    svc = QueueService(player_service=mock_player)
    result = svc.load_state()
    assert not result["ok"]
    assert result["error"] == "NO_SAVED_STATE"


def test_save_and_load_roundtrip(mock_player):
    svc = QueueService(player_service=mock_player)
    save = svc.save_state()
    assert save["ok"]
    load = svc.load_state()
    assert load["ok"]
    assert load["count"] > 0
    os.remove(save["path"])


def test_shutdown_saves_state(mock_player):
    svc = QueueService(player_service=mock_player)
    mock_player.set_queue = MagicMock()
    svc.shutdown()
    assert os.path.exists(_queue_state_path())
    os.remove(_queue_state_path())


def test_no_player_service():
    svc = QueueService()
    result = svc.save_state()
    assert not result["ok"]
    assert result["error"] == "NO_PLAYER"
    assert not svc.load_state()["ok"]
