"""Workflow: Disc Lab → Plan → Rip Job → Cancel."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("disc_lab"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestDiscLab:
    def test_disc_lab_bridge_methods(self, bootstrap, bridges):
        dl = bridges.get("disc_lab")
        assert dl is not None
        assert hasattr(dl, 'scanDisc')
        assert hasattr(dl, 'cover')
        assert hasattr(dl, 'rip_plan')
        assert hasattr(dl, 'startExtraction')
        assert hasattr(dl, 'cancelExtraction')

    def test_disc_lab_service_exists(self, bootstrap):
        svc = bootstrap.container.get("disc_lab_service")
        if svc is None:
            pytest.skip("disc_lab_service not registered (optional)")

    def test_qtest_navigate_disc_lab(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("disc_lab")
        assert nav.currentRoute == "disc_lab"
        page = find_qml_item(root_window, "discLabPage")
        assert page is not None, "discLabPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "disc_lab"
        assert page.property("visible") is True, "discLabPage should be visible after navigation"
