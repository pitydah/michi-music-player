"""Test QueueService persistence (save/load queue state)."""
import json
import os

import pytest

from core.queue_service import QueueService, _queue_state_path
pytestmark = [pytest.mark.qml_module("queue")]


_SAMPLE = [
    {"id": 1, "track_uid": "uid1", "title": "Track 1", "artist": "A",
     "album": "Al", "duration": 200, "filepath": "/path/1.flac", "source_type": "local_file"},
    {"id": 2, "track_uid": "uid2", "title": "Track 2", "artist": "B",
     "album": "Bl", "duration": 300, "filepath": "/path/2.flac", "source_type": "local_file"},
]


@pytest.fixture(autouse=True)
def clean_state():
    path = _queue_state_path()
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)


def test_queue_state_path_not_temp():
    path = _queue_state_path()
    assert path.endswith("queue_state.json")


def test_save_state():
    svc = QueueService()
    svc.set_items(_SAMPLE)
    result = svc.save_state()
    assert result["ok"]
    assert result["count"] == 2
    assert os.path.exists(result["path"])
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["version"] == 2
    assert "timestamp" in state
    assert len(state["items"]) == 2


def test_save_state_empty_queue():
    svc = QueueService()
    result = svc.save_state()
    assert result["ok"]
    assert result["count"] == 0


def test_load_state_no_saved_state():
    svc = QueueService()
    result = svc.load_state()
    assert not result["ok"]
    assert result["error"] == "NO_SAVED_STATE"


def test_save_and_load_roundtrip():
    svc = QueueService()
    svc.set_items(_SAMPLE)
    save = svc.save_state()
    assert save["ok"]
    load = svc.load_state()
    assert load["ok"]
    assert load["count"] == 2
    os.remove(save["path"])


def test_shutdown_saves_state():
    svc = QueueService()
    svc.set_items(_SAMPLE)
    svc.shutdown()
    assert os.path.exists(_queue_state_path())


def test_no_player_service():
    svc = QueueService()
    svc.set_items(_SAMPLE)
    result = svc.save_state()
    assert result["ok"]
    assert result["count"] == 2


def test_save_state_stores_version():
    svc = QueueService()
    svc.set_items(_SAMPLE)
    result = svc.save_state()
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["version"] == 2
