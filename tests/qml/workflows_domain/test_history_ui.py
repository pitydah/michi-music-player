"""Integration tests for HistoryPage UI: states, accessibility, keyboard, null bridge."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("history")]


class TestHistoryPage:
    """Verify HistoryPage loads, states, accessibility, keyboard, null bridge."""

    PAGE_QML = "ui_qml/pages/history/HistoryPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "history.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Historial"
        assert page.property("accessible_description") == "Historial de reproducción musical"

    def test_null_bridge_renders_unavailable(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("bridge") is None

    def test_bridge_connected(self, qml_harness):
        bridge = MagicMock()
        bridge.historyModel = []
        page = qml_harness.load_component(self.PAGE_QML, {
            "historyBridge": bridge
        })
        assert page.property("bridge") is not None

    def test_initial_state_loading(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("_state") == "LOADING"

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_refresh_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "historyBridge": bridge
        })
        page.refresh()
        bridge.refresh.assert_called_once()

    def test_refresh_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.refresh()

    def test_filter_events_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        result = page._filterEvents([])
        assert result == []

    def test_clear_all_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.clearAll()

    def test_clear_all_with_bridge(self, qml_harness):
        bridge = MagicMock()
        bridge.clearHistory.return_value = {"ok": True}
        page = qml_harness.load_component(self.PAGE_QML, {
            "historyBridge": bridge
        })
        page.clearAll()
        bridge.clearHistory.assert_called_once()
