"""DN — QueueService atomic persistence tests.

Persist: track_id, track_uid, current_index, position, shuffle_order,
repeat, source context, schema version.

Write temp file + atomic rename. Restore partial results with missing tracks.
No phantom tracks.
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
        {"track_id": "101", "track_uid": "u101", "title": "A", "artist": "X",
         "source_type": "local_file", "duration": 200, "filepath": "/a.flac"},
        {"track_id": "102", "track_uid": "u102", "title": "B", "artist": "Y",
         "source_type": "local_file", "duration": 300, "filepath": "/b.flac"},
        {"track_id": "103", "track_uid": "u103", "title": "C", "artist": "Z",
         "source_type": "local_file", "duration": 250, "filepath": "/c.flac"},
    ]


def test_persist_version(service, sample_items):
    service.set_items(sample_items)
    result = service.save_state()
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["version"] == 2


def test_persist_current_index(service, sample_items):
    service.set_items(sample_items, current_index=2)
    result = service.save_state()
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["current_index"] == 2


def test_persist_shuffle_repeat_context(service, sample_items):
    service.set_items(sample_items)
    service.shuffle_order = [2, 0, 1]
    service.repeat = "one"
    service.context = "album:42"
    result = service.save_state(position=30.0)
    with open(result["path"]) as f:
        state = json.load(f)
    assert state["shuffle_order"] == [2, 0, 1]
    assert state["repeat"] == "one"
    assert state["context"] == "album:42"
    assert state["position"] == 30.0


def test_persist_atomic_no_tmp_leftover(service, sample_items):
    service.set_items(sample_items)
    path = _queue_state_path()
    service.save_state()
    tmp_files = [f for f in os.listdir(os.path.dirname(path))
                 if f.startswith("queue_state.json.tmp")]
    assert len(tmp_files) == 0


def test_restore_partial_missing_tracks(service, sample_items):
    service.set_items(sample_items)
    service.save_state()
    fresh = QueueService()
    resolve_fn = MagicMock(side_effect=lambda item: item if item["track_id"] != "102" else None)
    result = fresh.load_state(resolve_fn=resolve_fn)
    assert result["ok"]
    assert result["count"] == 2
    assert result["partial"] is True
    assert "102" in result["missing_track_ids"]


def test_restore_missing_resolved_no_phantom(service, sample_items):
    service.set_items(sample_items)
    service.save_state()
    fresh = QueueService()
    resolve_fn = MagicMock(return_value=None)
    result = fresh.load_state(resolve_fn=resolve_fn)
    assert result["ok"]
    assert result["count"] == 0
    assert result["partial"] is True


def test_restore_no_save_state():
    svc = QueueService()
    result = svc.load_state()
    assert not result["ok"]
    assert result["error"] == "NO_SAVED_STATE"


def test_restore_preserves_order(service, sample_items):
    service.set_items(sample_items)
    service.shuffle_order = [2, 1, 0]
    service.save_state()
    fresh = QueueService()
    fresh.load_state()
    assert fresh.shuffle_order == [2, 1, 0]


def test_persist_track_uid_and_id(service, sample_items):
    service.set_items(sample_items)
    result = service.save_state()
    with open(result["path"]) as f:
        state = json.load(f)
    for item in state["items"]:
        assert "track_id" in item
        assert "track_uid" in item


def test_shutdown_persists(service, sample_items):
    service.set_items(sample_items, current_index=1)
    service.shutdown(position=15.0)
    assert os.path.exists(_queue_state_path())
