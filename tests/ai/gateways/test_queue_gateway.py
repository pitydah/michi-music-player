from __future__ import annotations

from core.assistant_gateways import ProductionQueueServiceGateway


class FakeQueueService:
    def __init__(self) -> None:
        self._queue: list[str] = []

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        self._queue.extend(paths)

    def get_queue(self) -> list[str]:
        return list(self._queue)

    def clear_queue(self) -> None:
        self._queue.clear()

    def play_queue(self, filepaths: list[str], start_index: int = 0) -> None:
        self._queue = list(filepaths)

    def reorder_queue(self, filepaths: list[str]) -> None:
        self._queue = list(filepaths)

    def enqueue_next(self, paths: list[str]) -> None:
        for p in reversed(paths):
            self._queue.insert(0, p)


class TestProductionQueueServiceGateway:
    def setup_method(self) -> None:
        self.qs = FakeQueueService()
        self.gw = ProductionQueueServiceGateway(self.qs)

    def test_get_empty_queue(self) -> None:
        r = self.gw.get_queue()
        assert r["ok"] is True
        assert r["count"] == 0

    def test_add_to_queue(self) -> None:
        r = self.gw.add_to_queue(["1", "2", "3"])
        assert r["ok"] is True
        assert r["added"] == 3

    def test_get_queue_after_add(self) -> None:
        self.gw.add_to_queue(["a", "b"])
        r = self.gw.get_queue()
        assert r["count"] == 2

    def test_clear_queue(self) -> None:
        self.gw.add_to_queue(["1", "2"])
        r = self.gw.clear_queue()
        assert r["ok"] is True
        assert r["count"] == 0
        verify = self.gw.get_queue()
        assert verify["count"] == 0

    def test_replace_queue(self) -> None:
        self.gw.add_to_queue(["old"])
        r = self.gw.replace_queue(["new1", "new2"])
        assert r["ok"] is True
        assert r["count"] == 2
        q = self.gw.get_queue()
        assert q["count"] == 2

    def test_remove_from_queue_valid(self) -> None:
        self.gw.add_to_queue(["1", "2", "3"])
        r = self.gw.remove_from_queue(1)
        assert r["ok"] is True
        q = self.gw.get_queue()
        assert q["count"] == 2

    def test_remove_from_queue_invalid(self) -> None:
        self.gw.add_to_queue(["1"])
        r = self.gw.remove_from_queue(99)
        assert r["ok"] is False

    def test_reorder_queue(self) -> None:
        self.gw.add_to_queue(["a", "b", "c"])
        r = self.gw.reorder_queue(0, 2)
        assert r["ok"] is True

    def test_unavailable(self) -> None:
        gw = ProductionQueueServiceGateway(None)
        r = gw.get_queue()
        assert r["ok"] is False
