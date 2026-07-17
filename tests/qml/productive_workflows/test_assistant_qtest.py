"""Workflow: Michi AI — QTest navigation and interaction."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("ai"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestAssistantQTest:
    def test_qtest_navigate_ai(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("ai")
        assert nav.currentRoute == "ai"
        page = find_qml_item(root_window, "assistantPage")
        assert page is not None, "assistantPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "ai"

    def test_qtest_ai_suggestions(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        ai_bridge = all_bridges.get("michi_ai")
        assert ai_bridge is not None
        nav.navigate("ai")
        assert nav.currentRoute == "ai"
        page = find_qml_item(root_window, "assistantPage")
        assert page is not None, "assistantPage not found"
        suggestion = find_qml_item(root_window, "suggestionCard")
        if suggestion is not None:
            qtest_click_item(suggestion, root_window)
            QTest.qWait(50)
            assert nav.currentRoute == "ai"
