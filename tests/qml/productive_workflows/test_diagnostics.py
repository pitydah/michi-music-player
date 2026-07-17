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
        assert refresh_btn is not None, "Refresh button not found in diagnosticsPage"
        from .conftest import wait_for_property, wait_for_condition
        state_before = getattr(diag_bridge, '_state', '') or getattr(diag_bridge, 'state', '')
        qtest_click_item(refresh_btn, root_window)
        wait_for_property(refresh_btn, "visible", True, timeout_ms=500)
        wait_for_condition(
            lambda: (getattr(diag_bridge, '_state', '') or getattr(diag_bridge, 'state', '')) != state_before,
            timeout_ms=500
        )
        QTest.qWait(200)
        assert nav.currentRoute == "diagnostics"
        diag_state = getattr(diag_bridge, '_state', '') or getattr(diag_bridge, 'state', '')
        assert diag_state != state_before, f"State should change: '{state_before}' -> '{diag_state}'"
