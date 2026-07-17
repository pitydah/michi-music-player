"""Workflow: PlaceholderPage — QTest navigation and interaction."""
from __future__ import annotations
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestPlaceholderPage:
    def test_qtest_navigate_placeholder(self, nav, root_window):
        from .conftest import find_qml_item, wait_for_property
        nav.navigate("placeholder")
        assert nav.currentRoute is not None
        page = find_qml_item(root_window, "placeholderPage")
        assert page is not None, "placeholderPage not found"
        wait_for_property(page, "visible", True, timeout_ms=500)
