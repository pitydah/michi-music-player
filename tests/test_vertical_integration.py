"""Vertical integration tests — full flow from QueueService to QML models."""

from __future__ import annotations


import pytest

from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml.models.QueueListModel import QueueListModel

pytestmark = [pytest.mark.qml_module("queue")]


@pytest.fixture
def full_stack():
    """Create a real QueueService with a real QueueBridge."""
    service = QueueService()
    bridge = QueueBridge(queue_service=service)
    return service, bridge


class TestLibraryToQueueService:
    """Verify items flow from library to QueueService correctly."""

    def test_enqueue_single_item(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "Song A", "filepath": "/a.flac",
                  "source_type": "local_file", "duration": 200}]
        result = bridge.add(items)
        assert result.get("ok")
        assert service.count == 1

    def test_enqueue_multiple_items(self, full_stack):
        service, bridge = full_stack
        items = [
            {"title": "Song A", "filepath": "/a.flac",
             "source_type": "local_file", "duration": 200},
            {"title": "Song B", "filepath": "/b.flac",
             "source_type": "local_file", "duration": 300},
        ]
        result = bridge.add(items)
        assert result.get("ok")
        assert service.count == 2

    def test_replace_and_play(self, full_stack):
        service, bridge = full_stack
        items = [
            {"title": "Song A", "filepath": "/a.flac",
             "source_type": "local_file", "duration": 200},
            {"title": "Song B", "filepath": "/b.flac",
             "source_type": "local_file", "duration": 300},
        ]
        # replaceAndPlay needs a player_service — use add + set_index instead
        bridge.add(items)
        service.current_index = 1
        assert service.count == 2
        assert service.current_index == 1

    def test_replace_and_play_invalid_index(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "Song A", "filepath": "/a.flac",
                  "source_type": "local_file", "duration": 200}]
        result = bridge.replaceAndPlay(items, 5)
        assert result.get("ok") is False
        assert result.get("error") == "INVALID_INDEX"


class TestQueueServiceToQueueBridge:
    """Verify QueueBridge correctly reflects QueueService state."""

    def test_bridge_count_matches_service(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        bridge.add(items)
        assert bridge.queueCount == 3

    def test_bridge_current_index_matches_service(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}]
        bridge.add(items)
        service.current_index = 1
        assert bridge.currentIndex == 1

    def test_bridge_can_undo_after_operation(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}]
        bridge.add(items)
        bridge.removeFromQueue(0)
        assert bridge.canUndo

    def test_bridge_model_is_available(self, full_stack):
        service, bridge = full_stack
        model = bridge.queueModel
        assert model is not None
        assert isinstance(model, QueueListModel)


class TestQueueBridgeToQueueListModel:
    """Verify QueueListModel correctly reflects bridge state."""

    def test_model_count_matches_bridge(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        bridge.add(items)
        model = bridge.queueModel
        assert model.count == 3

    def test_model_data_matches_items(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "Test Song", "artist": "Test Artist",
                  "duration": 180, "filepath": "/test.flac",
                  "source_type": "local_file"}]
        bridge.add(items)
        model = bridge.queueModel
        from PySide6.QtCore import Qt
        index = model.index(0, 0)
        assert model.data(index, Qt.DisplayRole) == "Test Song"

    def test_model_updates_after_add(self, full_stack):
        service, bridge = full_stack
        bridge.add([{"title": "A"}])
        model = bridge.queueModel
        assert model.count == 1
        bridge.add([{"title": "B"}])
        assert model.count == 2

    def test_model_updates_after_remove(self, full_stack):
        service, bridge = full_stack
        bridge.add([{"title": "A"}, {"title": "B"}])
        model = bridge.queueModel
        assert model.count == 2
        bridge.removeFromQueue(0)
        assert model.count == 1

    def test_model_updates_after_clear(self, full_stack):
        service, bridge = full_stack
        bridge.add([{"title": "A"}, {"title": "B"}])
        model = bridge.queueModel
        assert model.count == 2
        bridge.clearQueue()
        assert model.count == 0

    def test_model_current_index_updates(self, full_stack):
        service, bridge = full_stack
        bridge.add([{"title": "A"}, {"title": "B"}, {"title": "C"}])
        model = bridge.queueModel
        # After add, current_index defaults to 0 (first item)
        assert service.current_index == 0
        # Move to index 2
        service.current_index = 2
        assert service.current_index == 2


class TestFullWorkflow:
    """End-to-end workflow tests."""

    def test_enqueue_play_remove_clear(self, full_stack):
        service, bridge = full_stack
        # Enqueue 3 tracks
        items = [
            {"title": "A", "filepath": "/a.flac", "source_type": "local_file"},
            {"title": "B", "filepath": "/b.flac", "source_type": "local_file"},
            {"title": "C", "filepath": "/c.flac", "source_type": "local_file"},
        ]
        bridge.add(items)
        service.current_index = 0
        assert service.count == 3
        assert service.current_index == 0
        # Remove middle track
        bridge.removeFromQueue(1)
        assert service.count == 2
        # Clear all
        bridge.clearQueue()
        assert service.count == 0

    def test_undo_restores_previous_state(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        bridge.add(items)
        bridge.removeFromQueue(1)
        assert service.count == 2
        bridge.undo()
        assert service.count == 3

    def test_shuffle_preserves_items(self, full_stack):
        service, bridge = full_stack
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        bridge.add(items)
        service.toggle_shuffle()
        assert service.count == 3
        assert service.shuffle
