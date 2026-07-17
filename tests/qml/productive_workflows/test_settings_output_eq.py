"""Workflow: Settings → Change → Output Profile → EQ."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("settings"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestSettingsOutputEq:
    def test_settings_open_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("settings.open")
        assert a is not None, "settings.open action exists"

    def test_output_profiles_service(self, bootstrap):
        svc = bootstrap.container.get("output_profile_service")
        assert svc is not None
        assert hasattr(svc, 'list_profiles')

    def test_eq_service_methods(self, bootstrap):
        svc = bootstrap.container.get("equalizer_service")
        assert svc is not None
        assert hasattr(svc, 'set_bands')
        assert hasattr(svc, 'set_enabled')
        assert hasattr(svc, 'save_preset')
        assert hasattr(svc, 'load_preset')

    def test_qtest_navigate_eq(self, nav, root_window, all_bridges):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, wait_for_property
        eq_bridge = all_bridges.get("eq")
        assert eq_bridge is not None, "EqBridge should exist"
        nav.navigate("equalizer")
        assert nav.currentRoute == "equalizer"
        eq_page = find_qml_item(root_window, "equalizerPage")
        assert eq_page is not None, "equalizerPage not found"
        eq_page.forceActiveFocus()
        QTest.keyClick(eq_page, Qt.Key_Down)
        wait_for_property(eq_page, "visible", True, timeout_ms=500)
        QTest.qWait(50)
        assert nav.currentRoute == "equalizer"
        assert eq_bridge is not None
