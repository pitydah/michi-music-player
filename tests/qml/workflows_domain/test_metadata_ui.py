"""Integration tests for MetadataPage and MetadataInspectorPage UI."""
import pytest

pytestmark = [pytest.mark.qml_workflow("metadata")]


class TestMetadataPage:
    """Verify MetadataPage loads, states, null bridge, accessible props."""

    PAGE_QML = "ui_qml/pages/metadata/MetadataPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "metadata.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Editor de metadatos"
        assert page.property("accessible_description") == "Gestiona los metadatos de tus archivos de audio"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("mb") is None

    def test_initial_state(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("pageState") == "LOADING"

    def test_keyboard_navigation(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("focus") is True


class TestMetadataInspectorPage:
    """Verify MetadataInspectorPage loads, states, null bridge."""

    PAGE_QML = "ui_qml/pages/metadata/MetadataInspectorPage.qml"

    def test_page_object_name(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.objectName == "metadataInspector.page"

    def test_accessible_properties(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("accessible_role") == 2
        assert page.property("accessible_name") == "Inspector de metadatos"

    def test_null_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        assert page.property("md") is None

    def test_inspect_null_safe(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.inspect("/some/path")

    def test_start_edit_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.startEdit()

    def test_cancel_edit(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.setProperty("_editing", True)
        page.cancelEdit()
        assert page.property("_editing") is False

    def test_load_from_selection_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.loadFromSelection()

    def test_do_save_no_bridge(self, qml_harness):
        page = qml_harness.load_component(self.PAGE_QML, {})
        page.doSave()
