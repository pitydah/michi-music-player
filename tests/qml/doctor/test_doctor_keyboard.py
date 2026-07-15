"""Keyboard and accessibility tests for Library Doctor QML pages."""
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = [pytest.mark.qml_module("library_doctor"), pytest.mark.qml_dimension("accessibility")]

DOCTOR_FILES = [
    "pages/LibraryDoctorPage.qml",
    "pages/library_doctor/DoctorIssueDetail.qml",
    "pages/library_doctor/DoctorIssueList.qml",
    "pages/library_doctor/DoctorDryRunPage.qml",
    "pages/library_doctor/DoctorRepairProgress.qml",
    "pages/library_doctor/DoctorReportPage.qml",
]


class TestDoctorKeyboard:
    @pytest.mark.parametrize("rel_path", DOCTOR_FILES)
    def test_has_object_names(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "objectName:" in content, f"{rel_path} lacks objectName"
        count = content.count("objectName:")
        assert count >= 1, f"{rel_path} has too few objectName declarations ({count})"

    @pytest.mark.parametrize("rel_path", DOCTOR_FILES)
    def test_has_accessible(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "Accessible." in content, f"{rel_path} lacks Accessible declarations"

    @pytest.mark.parametrize("rel_path", DOCTOR_FILES)
    def test_has_keys_on_escape(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "Keys.onEscapePressed" in content, f"{rel_path} lacks Keys.onEscapePressed"

    @pytest.mark.parametrize("rel_path", DOCTOR_FILES)
    def test_has_focus_scope_or_focus_property(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "focus:" in content or "FocusScope" in content, \
            f"{rel_path} lacks focus management"

    def test_library_doctor_page_has_scan_button(self):
        p = QML_DIR / "pages/LibraryDoctorPage.qml"
        if not p.exists():
            pytest.skip("LibraryDoctorPage.qml not found")
        content = p.read_text()
        assert "objectName: \"doctorScanButton\"" in content
        assert "Accessible" in content

    def test_library_doctor_page_has_cancel_button(self):
        p = QML_DIR / "pages/LibraryDoctorPage.qml"
        if not p.exists():
            pytest.skip("LibraryDoctorPage.qml not found")
        content = p.read_text()
        assert "objectName: \"doctorCancelButton\"" in content

    def test_library_doctor_page_escape_cancels_scan(self):
        p = QML_DIR / "pages/LibraryDoctorPage.qml"
        if not p.exists():
            pytest.skip("LibraryDoctorPage.qml not found")
        content = p.read_text()
        assert "Keys.onEscapePressed" in content
        assert "cancelScan" in content

    def test_doctor_issue_list_has_select_buttons(self):
        p = QML_DIR / "pages/library_doctor/DoctorIssueList.qml"
        if not p.exists():
            pytest.skip("DoctorIssueList.qml not found")
        content = p.read_text()
        assert "objectName: \"doctorSelectAllButton\"" in content
        assert "objectName: \"doctorSelectNoneButton\"" in content

    def test_doctor_confirm_has_accessible_name(self):
        p = QML_DIR / "pages/library_doctor/DoctorDryRunPage.qml"
        if not p.exists():
            pytest.skip("DoctorDryRunPage.qml not found")
        content = p.read_text()
        assert "Accessible.name" in content

    def test_doctor_report_has_export_button(self):
        p = QML_DIR / "pages/library_doctor/DoctorReportPage.qml"
        if not p.exists():
            pytest.skip("DoctorReportPage.qml not found")
        content = p.read_text()
        assert "objectName: \"doctorExportReportButton\"" in content
        assert "objectName: \"doctorUndoAllButton\"" in content
