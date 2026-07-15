from __future__ import annotations
"""Comprehensive tests for Queue — 15+ tests.
Covers: reorder, remove, clear, undo, play item, selection, save playlist,
restore after restart, missing tracks, partial restore.
"""

import os

from unittest.mock import MagicMock

import pytest

from core.queue_service import QueueService, _queue_state_path
from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


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
def mock_player():
    p = MagicMock()
    p.get_queue.return_value = []
    p.set_queue = MagicMock()
    return p


class TestQueueCompleto:
    def test_empty_queue(self, service):
        assert service.count == 0
        assert service.items == []
        assert service.current_index == -1

    def test_add_item(self, service):
        service.add({"track_id": 1, "title": "A"})
        assert service.count == 1
        assert service.current_index == 0

    def test_reorder(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        service.add({"track_id": 3, "title": "C"})
        service.reorder(0, 2)
        assert service.items[2]["title"] == "A"

    def test_move(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        service.move(0, 1)
        assert service.items[1]["title"] == "A"

    def test_remove(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        service.remove([0])
        assert service.count == 1
        assert service.items[0]["title"] == "B"

    def test_clear(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        service.clear()
        assert service.count == 0
        assert service.current_index == -1

    def test_undo(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        service.clear()
        assert service.count == 0
        result = service.undo()
        assert result is True
        assert service.count == 2

    def test_undo_no_state(self, service):
        result = service.undo()
        assert result is False

    def test_get_current(self, service):
        service.add({"track_id": 1, "title": "A"})
        current = service.get_current()
        assert current["track_id"] == 1

    def test_get_current_empty(self, service):
        current = service.get_current()
        assert current is None

    def test_play_from_index(self, mock_player):
        bridge = QueueBridge(player_service=mock_player)
        mock_player.get_queue.return_value = [
            {"track_id": 1, "title": "A", "source_type": "local_file", "duration": 200},
            {"track_id": 2, "title": "B", "source_type": "local_file", "duration": 200},
        ]
        mock_player.play_index = MagicMock()
        result = bridge.playFromIndex(1)
        assert result["ok"]

    def test_save_state_persists(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.add({"track_id": 2, "title": "B"})
        result = service.save_state()
        assert result["ok"]
        assert os.path.exists(result["path"])

    def test_load_state_restores(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.save_state()
        fresh = QueueService()
        result = fresh.load_state()
        assert result["ok"]
        assert fresh.count == 1

    def test_missing_tracks(self, service):
        service.add({"track_id": 1, "title": "A", "filepath": "/a.flac"})
        service.add({"track_id": 2, "title": "B"})
        missing = service.missing_tracks()
        assert len(missing) == 1
        assert missing[0]["track_id"] == 2

    def test_partial_restore(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.save_state()
        fresh = QueueService()
        resolve_fn = MagicMock(side_effect=lambda item: item if item["track_id"] != 1 else None)
        result = fresh.load_state(resolve_fn=resolve_fn)
        assert result["ok"]
        assert result["missing_count"] == 1
        assert result["partial"] is True

    def test_shutdown_persists(self, service):
        service.add({"track_id": 1, "title": "A"})
        service.shutdown()
        assert os.path.exists(_queue_state_path())

    def test_shuffle_property(self, service):
        assert service.shuffle_order is None
        service.shuffle_order = [2, 0, 1]
        assert service.shuffle_order == [2, 0, 1]

    def test_repeat_property(self, service):
        assert service.repeat == "none"
        service.repeat = "all"
        assert service.repeat == "all"

    def test_context_property(self, service):
        assert service.context == ""
        service.context = "album:123"
        assert service.context == "album:123"

    def test_bridge_save_as_playlist(self, mock_player):
        mock_pb = MagicMock()
        mock_pb.saveQueueAsPlaylist.return_value = {"ok": True}
        bridge = QueueBridge(player_service=mock_player, playlists_bridge=mock_pb)
        result = bridge.saveAsPlaylist("My Queue")
        assert result["ok"]

    def test_bridge_no_player(self):
        bridge = QueueBridge()
        assert bridge.playFromIndex(0)["error"] == "NO_PLAYER"
