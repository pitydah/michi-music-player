from unittest.mock import MagicMock
from core.worker_manager import WorkerManager, CancellationToken


class TestWorkerManager:
    def test_create(self):
        mgr = WorkerManager(event_bus=MagicMock())
        assert mgr is not None

    def test_cancellation_token(self):
        ct = CancellationToken()
        assert not ct.is_set()
