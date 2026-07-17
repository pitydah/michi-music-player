"""Workflow: Queue → Reorder → Persist → Restore."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("queue"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestQueueReorderPersist:
    def test_queue_clear_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("queue.clear")
        assert a is not None, "queue.clear action exists"

    def test_queue_save_playlist_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("queue.save_playlist")
        assert a is not None, "queue.save_playlist action exists"

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

    def test_queue_bridge_exists(self, bootstrap, bridges):
        qb = bridges.get("queue")
        assert qb is not None

    def test_qtest_clear_queue_ui(self, nav, playback_bridge, root_window):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        playback_bridge.enqueueSong("1")
        playback_bridge.enqueueSong("2")
        qh = find_qml_item(root_window, "queueHeader")
        assert qh is not None, "queueHeader not found"
        clear_btn = find_qml_item(root_window, "clearQueueButton")
        assert clear_btn is not None, "clearQueueButton not found in queueHeader"
        qtest_click_item(clear_btn, root_window)
        QTest.qWait(50)
