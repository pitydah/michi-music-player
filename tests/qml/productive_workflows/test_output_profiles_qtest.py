"""Workflow: Output Profiles — QTest navigation and interaction."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("settings"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestOutputProfilesQTest:
    def test_qtest_navigate_outputs(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("outputs")
        assert nav.currentRoute == "outputs"
        page = find_qml_item(root_window, "outputProfilesPage")
        assert page is not None, "outputProfilesPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "outputs"

    def test_qtest_click_create_profile(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        nav.navigate("outputs")
        assert nav.currentRoute == "outputs"
        page = find_qml_item(root_window, "outputProfilesPage")
        assert page is not None, "outputProfilesPage not found"
        create_btn = None
        for child in page.childItems():
            text = child.property("text") if hasattr(child, 'property') else ""
            if "Crear" in str(text) or "Create" in str(text) or "New" in str(text):
                create_btn = child
                break
        assert create_btn is not None, "Create profile button not found"
        qtest_click_item(create_btn, root_window)
        QTest.qWait(50)
        assert nav.currentRoute == "outputs"
        op_bridge = all_bridges.get("output_profiles")
        if op_bridge is not None:
            profiles = getattr(op_bridge, 'profiles', None) or getattr(op_bridge, '_profiles', None)
            assert profiles is None or isinstance(profiles, (list, tuple))
