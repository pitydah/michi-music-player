"""Tests for engine-level enqueue_next semantics."""
from __future__ import annotations

from unittest.mock import MagicMock


def _insert_after_current(engine, paths):
    pos = engine._queue_index + 1
    engine._queue[pos:pos] = paths


class TestEngineEnqueueNext:
    def test_inserts_after_current_index(self):
        from audio.player import GStreamerEngine
        engine = GStreamerEngine.__new__(GStreamerEngine)
        engine._queue = ["/a/1.flac", "/a/2.flac", "/a/3.flac"]
        engine._queue_index = 0
        engine._shuffle = False
        engine._repeat = "none"
        engine._db = None
        engine._state = None
        engine.queue_changed = MagicMock()
        engine._transport = MagicMock()
        engine._transport.enqueue_next.side_effect = lambda p: _insert_after_current(engine, p)

        engine.enqueue_next(["/x/x1.flac", "/x/x2.flac"])

        assert engine._queue == [
            "/a/1.flac", "/x/x1.flac", "/x/x2.flac",
            "/a/2.flac", "/a/3.flac",
        ]
        assert engine._queue_index == 0

    def test_inserts_after_index_1(self):
        from audio.player import GStreamerEngine
        engine = GStreamerEngine.__new__(GStreamerEngine)
        engine._queue = ["/a/1.flac", "/a/2.flac", "/a/3.flac"]
        engine._queue_index = 1
        engine._shuffle = False
        engine._repeat = "none"
        engine._db = None
        engine._state = None
        engine.queue_changed = MagicMock()
        engine._transport = MagicMock()
        engine._transport.enqueue_next.side_effect = lambda p: _insert_after_current(engine, p)

        engine.enqueue_next(["/x/x1.flac"])

        assert engine._queue == [
            "/a/1.flac", "/a/2.flac", "/x/x1.flac",
            "/a/3.flac",
        ]

    def test_empty_queue_adds_but_does_not_play(self):
        from audio.player import GStreamerEngine
        engine = GStreamerEngine.__new__(GStreamerEngine)
        engine._queue = []
        engine._queue_index = -1
        engine._shuffle = False
        engine._repeat = "none"
        engine._db = None
        engine._state = None
        engine.queue_changed = MagicMock()
        engine._transport = MagicMock()
        engine._transport.enqueue_next.side_effect = lambda p: _insert_after_current(engine, p)

        engine.enqueue_next(["/x/x1.flac"])

        assert engine._queue == ["/x/x1.flac"]
        assert engine._queue_index == -1  # unchanged

    def test_empty_list_noop(self):
        from audio.player import GStreamerEngine
        engine = GStreamerEngine.__new__(GStreamerEngine)
        engine._queue = ["/a/1.flac"]
        engine._queue_index = 0
        engine._shuffle = False
        engine._repeat = "none"
        engine._db = None
        engine._state = None
        engine.queue_changed = MagicMock()
        engine._transport = MagicMock()
        engine._transport.enqueue_next.side_effect = lambda p: _insert_after_current(engine, p)

        engine.enqueue_next([])
        assert engine._queue == ["/a/1.flac"]

    def test_preserves_order_and_rest(self):
        from audio.player import GStreamerEngine
        engine = GStreamerEngine.__new__(GStreamerEngine)
        engine._queue = ["a", "b", "c", "d"]
        engine._queue_index = 2
        engine._shuffle = False
        engine._repeat = "none"
        engine._db = None
        engine._state = None
        engine.queue_changed = MagicMock()
        engine._transport = MagicMock()
        engine._transport.enqueue_next.side_effect = lambda p: _insert_after_current(engine, p)

        engine.enqueue_next(["x", "y"])

        assert engine._queue == ["a", "b", "c", "x", "y", "d"]
