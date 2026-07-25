"""QueueBridge contract tests — signals, commands, and property existence."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


def _queue_service(items=None, current_index=-1):
    service = MagicMock()
    state = {"items": list(items or []), "current_index": current_index}
    service.get_state.return_value = state
    service.items = list(state["items"])
    service.current_index = current_index
    service.subscribe.return_value = MagicMock()
    return service


class TestQueueBridgeSignals:
    """Verify granular signals exist and route correctly."""

    def test_has_data_changed_signal(self):
        bridge = QueueBridge(queue_service=_queue_service())
        assert hasattr(bridge, "dataChanged")

    def test_has_queue_changed_signal(self):
        bridge = QueueBridge(queue_service=_queue_service())
        assert hasattr(bridge, "queueChanged")

    def test_has_current_index_changed_signal(self):
        bridge = QueueBridge(queue_service=_queue_service())
        assert hasattr(bridge, "currentIndexChanged")

    def test_has_modes_changed_signal(self):
        bridge = QueueBridge(queue_service=_queue_service())
        assert hasattr(bridge, "modesChanged")

    def test_has_state_restored_signal(self):
        bridge = QueueBridge(queue_service=_queue_service())
        assert hasattr(bridge, "stateRestored")

    def test_operation_failed_does_not_emit(self):
        service = _queue_service()
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.queueChanged.connect(spy)
        bridge.currentIndexChanged.connect(spy)
        bridge.modesChanged.connect(spy)
        bridge.stateRestored.connect(spy)
        # Simulate operationFailed
        handler = service.subscribe.call_args[0][0]
        handler("operationFailed", {"error": "test"})
        spy.assert_not_called()

    def test_queue_changed_routes_to_queue_changed_signal(self):
        service = _queue_service([{"title": "A"}], current_index=0)
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.queueChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("queueChanged", {"operation": "add", "items": [{"title": "A"}], "current_index": 0})
        spy.assert_called_once()

    def test_current_index_routes_to_current_index_signal(self):
        service = _queue_service([{"title": "A"}], current_index=0)
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.currentIndexChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("currentIndexChanged", {"operation": "play_from_index", "current_index": 1})
        spy.assert_called_once()

    def test_modes_routes_to_modes_signal(self):
        service = _queue_service()
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.modesChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("modesChanged", {"operation": "set_repeat", "repeat": "all"})
        spy.assert_called_once()

    def test_state_restored_routes_to_state_restored_signal(self):
        service = _queue_service()
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.stateRestored.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("stateRestored", {"operation": "restore"})
        spy.assert_called_once()

    def test_data_changed_always_emitted_for_non_failure(self):
        service = _queue_service([{"title": "A"}], current_index=0)
        bridge = QueueBridge(queue_service=service)
        spy = MagicMock()
        bridge.dataChanged.connect(spy)
        handler = service.subscribe.call_args[0][0]
        handler("queueChanged", {"operation": "add"})
        assert spy.call_count >= 1


class TestQueueBridgeCommands:
    """Verify all expected commands exist and delegate correctly."""

    def test_add_delegates_to_enqueue(self):
        service = _queue_service()
        service.enqueue.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.add([{"title": "X"}])
        service.enqueue.assert_called_once_with([{"title": "X"}], play_now=False)

    def test_replace_and_play_delegates(self):
        service = _queue_service()
        service.replace_and_play.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.replaceAndPlay([{"title": "X"}], 0)
        service.replace_and_play.assert_called_once()

    def test_play_from_index_delegates(self):
        service = _queue_service()
        service.play_from_index.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.playFromIndex(3)
        service.play_from_index.assert_called_once_with(3)

    def test_remove_from_queue_delegates(self):
        service = _queue_service()
        service.remove.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.removeFromQueue(2)
        service.remove.assert_called_once_with([2])

    def test_move_item_delegates(self):
        service = _queue_service()
        service.reorder.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.moveItem(1, 3)
        service.reorder.assert_called_once_with(1, 3)

    def test_clear_queue_delegates(self):
        service = _queue_service()
        service.clear.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.clearQueue()
        service.clear.assert_called_once()

    def test_save_state_delegates(self):
        service = _queue_service()
        service.save_state.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.saveState()
        service.save_state.assert_called_once()

    def test_load_state_delegates(self):
        service = _queue_service()
        service.load_state.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.loadState()
        service.load_state.assert_called_once()

    def test_undo_delegates(self):
        service = _queue_service()
        service.undo.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.undo()
        service.undo.assert_called_once()

    def test_persist_delegates(self):
        service = _queue_service()
        service.persist.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.persist()
        service.persist.assert_called_once()

    def test_restore_delegates(self):
        service = _queue_service()
        service.restore.return_value = {"ok": True}
        bridge = QueueBridge(queue_service=service)
        result = bridge.restore()
        service.restore.assert_called_once()

    def test_missing_tracks_delegates(self):
        service = _queue_service()
        service.missing_tracks.return_value = []
        bridge = QueueBridge(queue_service=service)
        result = bridge.missingTracks()
        assert result == []


class TestQueueBridgeProperties:
    """Verify key properties exist and read from queue_service."""

    def test_can_undo_reads_from_service(self):
        service = _queue_service()
        service.can_undo = True
        bridge = QueueBridge(queue_service=service)
        assert bridge.property("canUndo") is True

    def test_queue_count_reads_from_model(self):
        service = _queue_service([{"title": "A"}, {"title": "B"}])
        bridge = QueueBridge(queue_service=service)
        assert bridge.property("queueCount") == 2

    def test_current_index_reads_from_service(self):
        service = _queue_service([{"title": "A"}], current_index=0)
        bridge = QueueBridge(queue_service=service)
        assert bridge.property("currentIndex") == 0

    def test_queue_model_is_available(self):
        service = _queue_service()
        bridge = QueueBridge(queue_service=service)
        model = bridge.property("queueModel")
        assert model is not None
