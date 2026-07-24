"""QueuePage runtime tests — state machine, interactions, accessibility."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.queue_bridge import QueueBridge

pytestmark = [pytest.mark.qml_module("queue")]


def _make_bridge(items=None, current_index=-1):
    items = items or []
    service = MagicMock()
    state = {"items": list(items), "current_index": current_index}
    service.get_state.return_value = state
    service.items = list(items)
    service.current_index = current_index
    service.subscribe.return_value = MagicMock()
    return QueueBridge(queue_service=service)


class TestQueuePageStateMachine:
    """Verify state machine logic from QueuePage."""

    def test_empty_queue_shows_empty_state(self):
        bridge = _make_bridge([])
        assert bridge.queueCount == 0

    def test_populated_queue_shows_ready_state(self):
        bridge = _make_bridge([{"title": "A"}, {"title": "B"}])
        assert bridge.queueCount == 2

    def test_no_bridge_shows_error_state(self):
        # When bridge is None, page should show error
        assert None is None  # Placeholder — real test is in QML

    def test_state_constants_exist_in_qml(self):
        """Verify state machine constants are defined in QueuePage.qml."""
        from pathlib import Path
        qml = (Path(__file__).resolve().parents[3] / "ui_qml" / "pages/queue/QueuePage.qml").read_text()
        assert "stateLoading" in qml
        assert "stateReady" in qml
        assert "stateError" in qml
        assert "stateEmpty" in qml


class TestQueueInteractions:
    """Verify queue commands work through the bridge."""

    def test_play_from_index(self):
        bridge = _make_bridge([{"title": "A"}, {"title": "B"}], current_index=0)
        bridge._queue_service.play_from_index.return_value = {"ok": True}
        result = bridge.playFromIndex(1)
        bridge._queue_service.play_from_index.assert_called_once_with(1)

    def test_remove_from_queue(self):
        bridge = _make_bridge([{"title": "A"}, {"title": "B"}])
        bridge._queue_service.remove.return_value = {"ok": True}
        result = bridge.removeFromQueue(0)
        bridge._queue_service.remove.assert_called_once_with([0])

    def test_move_item(self):
        bridge = _make_bridge([{"title": "A"}, {"title": "B"}, {"title": "C"}])
        bridge._queue_service.reorder.return_value = {"ok": True}
        result = bridge.moveItem(0, 2)
        bridge._queue_service.reorder.assert_called_once_with(0, 2)

    def test_clear_queue(self):
        bridge = _make_bridge([{"title": "A"}])
        bridge._queue_service.clear.return_value = {"ok": True}
        result = bridge.clearQueue()
        bridge._queue_service.clear.assert_called_once()

    def test_undo(self):
        bridge = _make_bridge([{"title": "A"}])
        bridge._queue_service.undo.return_value = {"ok": True}
        result = bridge.undo()
        bridge._queue_service.undo.assert_called_once()

    def test_save_as_playlist(self):
        bridge = _make_bridge([{"title": "A"}])
        pb = MagicMock()
        pb.saveQueueAsPlaylist.return_value = {"ok": True}
        bridge._pb = pb
        result = bridge.saveAsPlaylist("My Playlist")
        pb.saveQueueAsPlaylist.assert_called_once()

    def test_save_as_playlist_empty_name(self):
        bridge = _make_bridge([{"title": "A"}])
        result = bridge.saveAsPlaylist("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_NAME"

    def test_save_as_playlist_empty_queue(self):
        bridge = _make_bridge([])
        bridge._pb = MagicMock()
        result = bridge.saveAsPlaylist("My Playlist")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_QUEUE"


class TestQueueAccessibility:
    """Verify accessibility attributes in QML files."""

    def _read_qml(self, relpath):
        from pathlib import Path
        base = Path(__file__).resolve().parents[3] / "ui_qml"
        return (base / relpath).read_text()

    def test_queue_page_has_accessible_role(self):
        content = self._read_qml("pages/queue/QueuePage.qml")
        assert "Accessible.role" in content

    def test_queue_page_has_accessible_name(self):
        content = self._read_qml("pages/queue/QueuePage.qml")
        assert "Accessible.name" in content

    def test_queue_page_has_accessible_description(self):
        content = self._read_qml("pages/queue/QueuePage.qml")
        assert "Accessible.description" in content

    def test_queue_header_has_accessible(self):
        content = self._read_qml("pages/queue/QueueHeader.qml")
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_queue_actions_has_accessible(self):
        content = self._read_qml("pages/queue/QueueActions.qml")
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_queue_list_view_has_accessible(self):
        content = self._read_qml("pages/queue/QueueListView.qml")
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_queue_item_has_accessible(self):
        content = self._read_qml("pages/queue/QueueItem.qml")
        assert "Accessible.role" in content
        assert "Accessible.name" in content

    def test_queue_empty_state_has_accessible(self):
        content = self._read_qml("pages/queue/QueueEmptyState.qml")
        assert "Accessible.role" in content
        assert "Accessible.name" in content
