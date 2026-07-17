from unittest.mock import MagicMock
from core.queue_service import QueueService


class TestQueueService:
    def test_create(self):
        svc = QueueService(player_service=MagicMock(), event_bus=MagicMock())
        assert svc._items == []

    def test_queue_empty_by_default(self):
        svc = QueueService()
        assert len(svc._items) == 0
