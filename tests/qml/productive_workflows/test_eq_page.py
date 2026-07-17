"""Workflow: EqPage — QTest navigation and interaction."""
from __future__ import annotations
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

pytestmark = [
    pytest.mark.qml_module("equalizer"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestEqPage:
    def test_qtest_navigate_eq(self, nav, root_window):
        from .conftest import find_qml_item, wait_for_property
        nav.navigate("equalizer")
        assert nav.currentRoute == "equalizer"
        page = find_qml_item(root_window, "eqPage")
        assert page is not None, "eqPage not found"
        wait_for_property(page, "visible", True, timeout_ms=500)
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "equalizer"
