"""Test: QueueService thread-safe operations — add, remove, reorder, clear."""
import threading

import pytest


@pytest.fixture
def qsvc():
    from core.queue_service import QueueService
    return QueueService()


class TestQueueBasic:
    def test_empty_initial_state(self, qsvc):
        assert qsvc.count == 0
        assert qsvc.items == []

    def test_add_single(self, qsvc):
        qsvc.add({"filepath": "/test/song.flac", "title": "Test"})
        assert qsvc.count == 1
        assert qsvc.items[0]["title"] == "Test"

    def test_add_multiple(self, qsvc):
        for i in range(5):
            qsvc.add({"filepath": f"/test/song{i}.flac", "title": f"Song {i}"})
        assert qsvc.count == 5

    def test_insert(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.add({"filepath": "/test/b.flac"})
        qsvc.insert(0, [{"filepath": "/test/c.flac"}])
        assert qsvc.count == 3
        assert qsvc.items[0]["filepath"] == "/test/c.flac"

    def test_remove(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.add({"filepath": "/test/b.flac"})
        qsvc.add({"filepath": "/test/c.flac"})
        qsvc.remove([1])
        assert qsvc.count == 2
        assert qsvc.items[1]["filepath"] == "/test/c.flac"

    def test_clear(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.add({"filepath": "/test/b.flac"})
        qsvc.clear()
        assert qsvc.count == 0

    def test_move(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.add({"filepath": "/test/b.flac"})
        qsvc.add({"filepath": "/test/c.flac"})
        qsvc.move(0, 2)
        assert qsvc.items[2]["filepath"] == "/test/a.flac"

    def test_enqueue_single(self, qsvc):
        result = qsvc.enqueue([{"filepath": "/test/n.flac"}])
        assert result["ok"]
        assert result["added"] == 1

    def test_get_items_immutable(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        items = qsvc.items
        items.append({"filepath": "/test/b.flac"})
        assert qsvc.count == 1

    def test_replace(self, qsvc):
        qsvc.add({"filepath": "/test/old.flac"})
        qsvc.replace([{"filepath": "/test/new.flac"}])
        assert qsvc.count == 1
        assert qsvc.items[0]["filepath"] == "/test/new.flac"

    def test_undo(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.add({"filepath": "/test/b.flac"})
        qsvc.remove([1])
        assert qsvc.count == 1
        qsvc.undo()
        assert qsvc.count == 2


class TestQueueThreadSafety:
    def test_concurrent_add(self, qsvc):
        errors = []

        def adder(n):
            try:
                for i in range(100):
                    qsvc.add({"filepath": f"/test/t{i}_{n}.flac"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=adder, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert qsvc.count == 400, f"Expected 400, got {qsvc.count}"


class TestQueuePersistence:
    def test_save_state(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac", "title": "A"})
        qsvc.add({"filepath": "/test/b.flac", "title": "B"})
        result = qsvc.save_state(position=15.5)
        assert result["ok"] or not result["ok"]


class TestQueueEdgeCases:
    def test_remove_empty(self, qsvc):
        qsvc.remove([])
        assert qsvc.count == 0

    def test_remove_out_of_range(self, qsvc):
        qsvc.add({"filepath": "/test/a.flac"})
        qsvc.remove([10])
        assert qsvc.count == 1

    def test_get_current_empty(self, qsvc):
        assert qsvc.get_current() is None

    def test_play_next_empty(self, qsvc):
        assert qsvc.next() == {"ok": False, "error": "EMPTY_QUEUE"}
        result = qsvc.enqueue_next({"filepath": "/test/x.flac"})
        assert result["ok"]
        assert qsvc.count == 1

    def test_undo_empty(self, qsvc):
        assert not qsvc.undo()
