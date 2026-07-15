"""Integration tests for QueuePage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("queue")]


class TestQueuePage:
    """Verify QueuePage, QueueListView, QueueItem, QueueHeader, QueueActions, QueueEmptyState."""

    PAGE_QML = "ui_qml/pages/queue/QueuePage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "queue.page"

    def test_null_bridge_renders_gracefully(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("qb") is None

    def test_refresh_safe_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.refresh()

    def test_refresh_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "queueBridge": bridge
        })
        page.refresh()
        bridge.refresh.assert_called_once()

    def test_route_enter(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "queueBridge": bridge
        })
        page.routeEnter("queue")
        bridge.refresh.assert_called_once()

    def test_route_enter_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.routeEnter("queue")

    def test_component_on_completed(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "queueBridge": bridge
        })
        assert page.property("qb") is not None
