"""Test QueueService atomic persistence (write temp + rename).

Persists: track_id, track_uid, source, current_index, position,
shuffle_order, repeat, context.
Restores: resolves IDs, marks missing, preserves order.
"""
from __future__ import annotations

import json
import os

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService, _queue_state_path


@pytest.fixture(autouse=True)
def clean_state():
    path = _queue_state_path()
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def service():
    return QueueService()


@pytest.fixture
def sample_items():
    return [
        {"track_id": "101", "track_uid": "u101", "title": "Song A",
         "artist": "X", "source_type": "local_file", "duration": 200},
        {"track_id": "102", "track_uid": "u102", "title": "Song B",
         "artist": "Y", "source_type": "local_file", "duration": 300},
        {"track_id": "103", "track_uid": "u103", "title": "Song C",
         "artist": "Z", "source_type": "local_file", "duration": 250},
    ]


def test_save_state_stores_required_fields(service, sample_items):
    service.set_items(sample_items, current_index=1)
    service.shuffle_order = [2, 0, 1]
    service.repeat = "all"
    service.context = "album:123"
    result = service.save_state(position=45.5)
    assert result["ok"]
    assert result["count"] == 3
    path = result["path"]
    assert os.path.exists(path)
    with open(path) as f:
        state = json.load(f)
    assert state["version"] == 2
    assert state["current_index"] == 1
    assert state["position"] == 45.5
    assert state["shuffle_order"] == [2, 0, 1]
    assert state["repeat"] == "all"
    assert state["context"] == "album:123"
    assert len(state["items"]) == 3
    for item in state["items"]:
        assert "track_id" in item
        assert "track_uid" in item
        assert "source" in item


def test_save_state_atomic_write_temp_then_rename(service, sample_items):
    service.set_items(sample_items)
    path = _queue_state_path()
    result = service.save_state()
    assert result["ok"]
    assert os.path.exists(path)
    tmp_files = [f for f in os.listdir(os.path.dirname(path)) if f.startswith("queue_state.json.tmp")]
    assert len(tmp_files) == 0


def test_save_state_empty_queue(service):
    result = service.save_state()
    assert result["ok"]
    assert result["count"] == 0


def test_load_state_restores_full_state(service, sample_items):
    service.set_items(sample_items, current_index=2)
    service.shuffle_order = [0, 2, 1]
    service.repeat = "one"
    service.context = "playlist:42"
    service.save_state()
    fresh = QueueService()
    result = fresh.load_state()
    assert result["ok"]
    assert result["count"] == 3
    assert fresh.count == 3
    assert fresh.current_index == 2
    assert fresh.repeat == "one"
    assert fresh.context == "playlist:42"


def test_load_state_resolves_tracks(service, sample_items):
    service.set_items(sample_items)
    service.save_state()
    fresh = QueueService()
    resolve_fn = MagicMock(side_effect=lambda item: item if item["track_id"] != "102" else None)
    result = fresh.load_state(resolve_fn=resolve_fn)
    assert result["ok"]
    assert result["count"] == 2
    assert result["missing_count"] == 1
    assert result["partial"] is True
    assert "102" in result["missing_track_ids"]


def test_load_state_no_saved_state():
    svc = QueueService()
    result = svc.load_state()
    assert not result["ok"]
    assert result["error"] == "NO_SAVED_STATE"


def test_load_state_preserves_order(service, sample_items):
    service.set_items(sample_items)
    service.shuffle_order = [2, 1, 0]
    service.save_state()
    fresh = QueueService()
    fresh.load_state()
    assert fresh.items[0]["track_id"] == "101"
    assert fresh.items[1]["track_id"] == "102"
    assert fresh.items[2]["track_id"] == "103"
    assert fresh.shuffle_order == [2, 1, 0]


def test_shutdown_calls_save_state(service, sample_items):
    service.set_items(sample_items)
    service.shutdown(position=10.0)
    path = _queue_state_path()
    assert os.path.exists(path)
