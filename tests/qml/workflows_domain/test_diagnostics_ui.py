"""Integration tests for DiagnosticsPage UI."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("diagnostics")]


class TestDiagnosticsPage:
    """Verify DiagnosticsPage loads, states, accessibility, null bridge."""

    PAGE_QML = "ui_qml/pages/DiagnosticsPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "diagnostics.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Diagnóstico"
        assert page.property("accessible_description") == "Panel de diagnóstico del sistema"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("diag") is None

    def test_route_enter_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.routeEnter("diagnostics")

    def test_route_enter_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "diagnosticsBridge": bridge
        })
        page.routeEnter("diagnostics")
        bridge.refresh.assert_called_once()

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True
