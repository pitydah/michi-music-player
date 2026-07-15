"""Integration tests for OutputProfilesPage UI."""
import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.qml_workflow("output_profiles")]


class TestOutputProfilesPage:
    """Verify OutputProfilesPage loads, states, accessible props, null bridge."""

    PAGE_QML = "ui_qml/pages/OutputProfilesPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "outputProfilesPage"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 3
        assert page.property("accessible_name") == "Perfiles de salida"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("op") is None

    def test_refresh_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.refresh()

    def test_refresh_with_bridge(self, qml_harness):
        bridge = MagicMock()
        page = qml_harness.load_component(self.PAGE_QML, {
            "outputProfilesBridge": bridge
        })
        page.refresh()
        bridge.refresh.assert_called_once()

    def test_select_profile_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.selectProfile("test")

    def test_select_profile_with_bridge(self, qml_harness):
        bridge = MagicMock()
        bridge.setActiveProfile.return_value = {"ok": True}
        page = qml_harness.load_component(self.PAGE_QML, {
            "outputProfilesBridge": bridge
        })
        page.selectProfile("test_id")
        bridge.setActiveProfile.assert_called_once_with("test_id")

    def test_duplicate_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.duplicate("test")

    def test_remove_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.remove("test")

    def test_initial_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("_state") == "LOADING"
