"""Integration tests for LibraryDoctorPage UI."""
import pytest

pytestmark = [pytest.mark.qml_workflow("library_doctor")]


class TestLibraryDoctorPage:
    """Verify LibraryDoctorPage loads, states, accessibility, null bridge."""

    PAGE_QML = "ui_qml/pages/LibraryDoctorPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "libraryDoctorPage"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 3
        assert page.property("accessible_name") == "Diagnóstico de biblioteca"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("doc") is None

    def test_cap_null(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page._cap() is False

    def test_initial_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("_state") == "LOADING"

    def test_keyboard_escape_safe(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.event("keyPress", {"key": 16777216})
