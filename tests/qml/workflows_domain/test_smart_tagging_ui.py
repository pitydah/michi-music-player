"""Integration tests for SmartTaggingPage UI."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("smart_tagging")]


class TestSmartTaggingPage:
    """Verify SmartTaggingPage loads, states, accessibility, null bridge."""

    PAGE_QML = "ui_qml/pages/SmartTaggingPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "smartTagging.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Smart Tagging"
        assert page.property("accessible_description") == "Sugerencias automáticas de metadatos para tu biblioteca musical"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("stb") is None
        assert page.property("pageState") == "ERROR"

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True

    def test_bridge_connected_idle(self, qml_harness):
        bridge = MagicMock()
        bridge.status = "idle"
        page = qml_harness.load_component(self.PAGE_QML, {
            "smartTaggingBridge": bridge
        })
        assert page.property("pageState") == "READY"

    def test_bridge_scanning(self, qml_harness):
        bridge = MagicMock()
        bridge.status = "scanning"
        page = qml_harness.load_component(self.PAGE_QML, {
            "smartTaggingBridge": bridge
        })
        assert page.property("pageState") == "ANALYZING"

    def test_escape_clears_error(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setProperty("_errorMsg", "some error")
        page.setProperty("_confirmApply", True)
        page.event("keyPress", {"key": 16777216})
        assert page.property("_errorMsg") == ""
        assert page.property("_confirmApply") is False
