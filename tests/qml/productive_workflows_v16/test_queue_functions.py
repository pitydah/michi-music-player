"""Workflow: Queue functions — add, remove, clear, reorder, save."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("queue"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestQueueFunctions:
    def test_queue_remove_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("queue.remove")
        assert a is not None and a.handler is not None

    def test_queue_clear_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("queue.clear")
        assert a is not None and a.handler is not None

    def test_queue_save_playlist_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("queue.save_playlist")
        assert a is not None and a.handler is not None

    def test_queue_bridge_enqueue(self, bootstrap):
        qb = bootstrap._bridges.get("queue")
        assert qb is not None
        assert hasattr(qb, 'enqueue')

    def test_queue_service_add(self, bootstrap):
        svc = bootstrap.container.get("queue_service")
        r = svc.enqueue([{"filepath": "/test/song.flac", "title": "Test"}])
        assert r.get("ok") or r.get("added", 0) > 0
