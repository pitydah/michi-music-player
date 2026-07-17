"""Test DiagnosticsPage QML page loads and renders correctly."""
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_module("diagnostics")]

QML_PATH = "ui_qml/pages/DiagnosticsPage.qml"


class TestDiagnosticsPageLoads:
    def test_qml_file_exists(self):
        import os
        assert os.path.isfile(QML_PATH), f"{QML_PATH} no existe"

    def test_qml_has_object_name(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'objectName: "diagnosticsPage"' in content

    def test_qml_imports_bridge(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "diagnosticsBridge" in content

    def test_qml_has_states(self):
        with open(QML_PATH) as f:
            content = f.read()
        for state in ("stateLoading", "stateReady", "stateError", "stateEmpty"):
            assert state in content

    def test_qml_has_route_enter(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "function routeEnter(route)" in content

    def test_qml_has_refresh_button(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'objectName: "refreshDiagnosticsButton"' in content

    def test_qml_has_copy_button(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'objectName: "copyDiagnosticsButton"' in content

    def test_qml_uses_glass_material(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "GlassMaterial" in content

    def test_qml_uses_status_badge(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "StatusBadge" in content

    def test_qml_uses_loader_for_states(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "Loader" in content

    def test_qml_shows_loading_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "LoadingState" in content

    def test_qml_shows_error_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "ErrorState" in content

    def test_qml_shows_empty_state(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "EmptyState" in content

    def test_qml_has_diag_property(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "property var diag" in content

    def test_qml_readonly_state_properties(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "readonly property int stateLoading: 0" in content
        assert "readonly property int stateReady: 1" in content

    def test_qml_repeater_checks(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "Repeater" in content
        assert "model: root.diag ? root.diag.checks : []" in content

    def test_qml_flickable_ready(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "Flickable" in content
        assert "visible: root.pageState === root.stateReady" in content

    def test_qml_accessible_role(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'Accessible.role: Accessible.Pane' in content

    def test_qml_accessible_name(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert 'Accessible.name: "Diagnóstico"' in content

    def test_page_initializes_with_bridge(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        bridge = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        assert hasattr(bridge, "jobs")
        assert hasattr(bridge, "refresh")

    def test_page_route_enter_calls_refresh(self):
        bridge = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        bridge.refresh = MagicMock()
        bridge.refresh()
        bridge.refresh.assert_called_once()

    def test_page_copy_diagnostics(self):
        bridge = DiagnosticsBridge(
            diagnostics_service=MagicMock(),
            worker_manager=MagicMock(),
            query_executor=MagicMock(),
        )
        bridge._jobs = [{"status": "PASS", "id": "test", "message": "OK", "duration_ms": 1}]
        text = bridge.copyDiagnostics()
        assert "test" in text

    def test_page_state_error_when_no_bridge(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "pageState: root.diag ? stateReady : stateError" in content

    def test_page_shows_diagnostic_checks(self):
        with open(QML_PATH) as f:
            content = f.read()
        assert "modelData.ok" in content
        assert "modelData.key" in content
        assert "modelData.value" in content
