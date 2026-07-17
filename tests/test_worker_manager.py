from core.worker_manager import WorkerManager, CancellationToken


class TestWorkerManager:
    def test_create(self):
        mgr = WorkerManager()
        assert mgr is not None

    def test_cancellation_token(self):
        ct = CancellationToken()
        assert not ct._event.is_set()
