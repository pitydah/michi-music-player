"""Workflow: Library Doctor — QTest navigation and interaction."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("library_doctor"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestLibraryDoctorQTest:
    def test_qtest_navigate_doctor(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("library_doctor")
        assert nav.currentRoute == "library_doctor"
        page = find_qml_item(root_window, "libraryDoctorScanPage")
        assert page is not None, "libraryDoctorScanPage not found"
        page.forceActiveFocus()
        QTest.keyClick(page, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "library_doctor"

    def test_qtest_click_scan(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        doctor_bridge = all_bridges.get("library_doctor")
        assert doctor_bridge is not None
        nav.navigate("library_doctor")
        assert nav.currentRoute == "library_doctor"
        scan_page = find_qml_item(root_window, "libraryDoctorScanPage")
        assert scan_page is not None, "libraryDoctorScanPage not found"
        scan_btn = find_qml_item(root_window, "scanLibraryButton")
        assert scan_btn is not None, "scanLibraryButton not found"
        from .conftest import wait_for_condition
        status_before = getattr(doctor_bridge, 'status', '') or getattr(doctor_bridge, '_state', '')
        qtest_click_item(scan_btn, root_window)
        wait_for_condition(
            lambda: (getattr(doctor_bridge, 'status', '') or getattr(doctor_bridge, '_state', '')) != status_before,
            timeout_ms=500
        )
        QTest.qWait(100)
        assert nav.currentRoute == "library_doctor"
        status_after = getattr(doctor_bridge, 'status', '') or getattr(doctor_bridge, '_state', '')
        assert status_after != status_before, f"Doctor status should change: '{status_before}' -> '{status_after}'"
