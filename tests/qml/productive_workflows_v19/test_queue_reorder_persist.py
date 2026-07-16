"""Workflow: Queue → Reorder → Persist → Restore."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("queue"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestQueueReorderPersist:
    def test_queue_clear_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("queue.clear")
        assert a is not None and a.handler is not None

    def test_queue_save_playlist_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("queue.save_playlist")
        assert a is not None and a.handler is not None

    def test_queue_service_methods(self, bootstrap):
        svc = bootstrap.container.get("queue_service")
        assert svc is not None
        assert hasattr(svc, 'enqueue')
        assert hasattr(svc, 'remove')
        assert hasattr(svc, 'clear')
        assert hasattr(svc, 'reorder')
        assert hasattr(svc, 'undo')
        assert hasattr(svc, 'save_state')
        assert hasattr(svc, 'load_state')

    def test_queue_bridge_exists(self, bootstrap):
        qb = bootstrap._bridges.get("queue")
        assert qb is not None
