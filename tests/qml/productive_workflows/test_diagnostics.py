"""Workflow: Diagnostics → Health Check."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("diagnostics"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestDiagnostics:
    def test_diagnostics_open_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("diagnostics.open")
        assert a is not None, "diagnostics.open action exists"

    def test_diagnostics_service_methods(self, bootstrap):
        svc = bootstrap.container.get("diagnostics_service")
        assert svc is not None
        assert hasattr(svc, 'check_all')
        assert hasattr(svc, 'check_database')
        assert hasattr(svc, 'check_library')
        assert hasattr(svc, 'health')

    def test_qtest_click_refresh(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        diag_bridge = all_bridges.get("diagnostics")
        assert diag_bridge is not None
        nav.navigate("diagnostics")
        assert nav.currentRoute == "diagnostics"
        diag_page = find_qml_item(root_window, "diagnosticsPage")
        assert diag_page is not None, "diagnosticsPage not found"
        refresh_btn = None
        for child in diag_page.childItems():
            text = child.property("text") if hasattr(child, 'property') else ""
            if "Refrescar" in str(text) or "Refresh" in str(text):
                refresh_btn = child
                break
        if refresh_btn is not None:
            qtest_click_item(refresh_btn, root_window)
            QTest.qWait(200)
