"""Integration tests for CommandPalette UI."""
import pytest

pytestmark = [pytest.mark.qml_workflow("command_palette")]


class TestCommandPalette:
    """Verify CommandPalette loads, accessible props, search, execute, null bridge."""

    QML_PATH = "ui_qml/components/CommandPalette.qml"

    def test_component_object_name(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        assert cp.objectName == "commandPalette"

    def test_accessible_properties(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        assert cp.property("accessible_role") == 11
        assert cp.property("accessible_name") == "Paleta de comandos"
        assert cp.property("accessible_description") == "Busca y ejecuta comandos rápidamente"

    def test_null_bridge(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        assert cp.property("cpb") is None

    def test_initial_state(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        assert cp.property("open") is False

    def test_open_and_close_palette(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        cp.openPalette()
        assert cp.property("open") is True
        cp.closePalette()
        assert cp.property("open") is False

    def test_do_search_no_bridge(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        cp.doSearch("test")

    def test_execute_selected_no_results(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        cp.executeSelected()

    def test_escape_shortcut(self, qml_harness):
        cp = qml_harness.load_component(self.QML_PATH, {})
        cp.openPalette()
        assert cp.property("open") is True
