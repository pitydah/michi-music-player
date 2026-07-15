"""Tests for Queue v12 — single source of truth, no parallel queue in QML."""
from unittest.mock import MagicMock, patch

import pytest


class TestQueueBridgeCreation:
    def test_requires_player_service(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        with pytest.raises(Exception):
            QueueBridge()

    def test_creation_with_player(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock())
        assert qb is not None

    def test_has_queue_model(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock())
        assert qb.queueModel is not None

    def test_queue_count_default(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock())
        assert qb.queueCount >= 0


class TestQueueOperations:
    def test_refresh(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock())
        result = qb.refresh()
        assert result.get("ok")

    def test_play_from_index(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock())
        result = qb.playFromIndex(0)
        assert isinstance(result, dict)

    def test_clear_queue(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=MagicMock(), queue_service=MagicMock())
        result = qb.clearQueue()
        assert isinstance(result, dict)

    def test_save_state(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qs = MagicMock()
        qs.save_state.return_value = {"ok": True}
        qb = QueueBridge(player_service=MagicMock(), queue_service=qs)
        result = qb.saveState()
        assert isinstance(result, dict)

    def test_load_state(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qs = MagicMock()
        qs.load_state.return_value = {"ok": True}
        qb = QueueBridge(player_service=MagicMock(), queue_service=qs)
        result = qb.loadState()
        assert isinstance(result, dict)

    def test_persist(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qs = MagicMock()
        qs.persist.return_value = {"ok": True}
        qb = QueueBridge(player_service=MagicMock(), queue_service=qs)
        result = qb.persist()
        assert isinstance(result, dict)

    def test_restore(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qs = MagicMock()
        qs.restore.return_value = {"ok": True}
        qb = QueueBridge(player_service=MagicMock(), queue_service=qs)
        result = qb.restore()
        assert isinstance(result, dict)

    def test_missing_tracks(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qs = MagicMock()
        qs.missing_tracks.return_value = []
        qb = QueueBridge(player_service=MagicMock(), queue_service=qs)
        result = qb.missingTracks()
        assert isinstance(result, list)
