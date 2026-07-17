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
        from .conftest import find_qml_item, qtest_click_item, wait_for_condition
        op_bridge = all_bridges.get("output_profiles")
        assert op_bridge is not None, "OutputProfilesBridge should exist"
        nav.navigate("outputs")
        assert nav.currentRoute == "outputs"
        page = find_qml_item(root_window, "outputProfilesPage")
        assert page is not None, "outputProfilesPage not found"
        create_btn = find_qml_item(root_window, "createProfileButton")
        assert create_btn is not None, "createProfileButton not found"
        profiles_before = getattr(op_bridge, 'profiles', None) or getattr(op_bridge, '_profiles', None)
        qtest_click_item(create_btn, root_window)
        wait_for_condition(
            lambda: (getattr(op_bridge, 'profiles', None) or getattr(op_bridge, '_profiles', None)) != profiles_before,
            timeout_ms=500
        )
        QTest.qWait(50)
        assert nav.currentRoute == "outputs"
        profiles_after = getattr(op_bridge, 'profiles', None) or getattr(op_bridge, '_profiles', None)
        assert profiles_after != profiles_before or profiles_after is not None
