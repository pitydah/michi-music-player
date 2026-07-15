"""Tests keyboard navigation, focus, and accessibility for History QML pages."""
import pytest
from pathlib import Path

pytestmark = [pytest.mark.qml_module("history")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
HISTORY_FILES = [
    "HistoryPage.qml",
    "HistoryTimeline.qml",
    "HistoryTable.qml",
    "HistoryFilterBar.qml",
    "HistoryRetentionDialog.qml",
    "HistoryExportDialog.qml",
    "HistoryStatisticsPage.qml",
]


class TestHistoryKeyboard:

    @pytest.fixture(params=HISTORY_FILES)
    def qml_file(self, request):
        p = QML_DIR / "pages" / "history" / request.param
        return p

    def test_file_has_focus_scope(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        if "Dialog" in content or "Item" in content:
            assert "FocusScope" in content or "activeFocusOnTab" in content or "Keys.on" in content, \
                f"{qml_file.name} lacks focus/keyboard handling"

    def test_file_has_key_navigation(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        assert "KeyNavigation.tab" in content or "KeyNavigation.backtab" in content, \
            f"{qml_file.name} lacks KeyNavigation chains"

    def test_file_has_escape_key(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        assert "Keys.onEscapePressed" in content, \
            f"{qml_file.name} lacks Escape key handling"

    def test_file_has_object_names(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        count = content.count("objectName:")
        assert count >= 2, f"{qml_file.name} has too few objectName declarations ({count})"

    def test_file_has_accessible(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        assert "Accessible." in content, \
            f"{qml_file.name} lacks Accessible properties"

    def test_file_has_michi_theme(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        assert "MichiTheme." in content, \
            f"{qml_file.name} lacks MichiTheme usage"

    def test_history_page_focus_scope(self):
        p = QML_DIR / "pages" / "history" / "HistoryPage.qml"
        content = p.read_text()
        assert "activeFocusOnTab" in content
        assert "KeyNavigation.tab" in content

    def test_retention_dialog_focus_trap(self):
        p = QML_DIR / "pages" / "history" / "HistoryRetentionDialog.qml"
        content = p.read_text()
        assert "FocusScope" in content
        assert "activeFocusOnTab" in content

    def test_export_dialog_focus_trap(self):
        p = QML_DIR / "pages" / "history" / "HistoryExportDialog.qml"
        if p.exists():
            content = p.read_text()
            assert "FocusScope" in content
            assert "activeFocusOnTab" in content

    def test_statistics_page_keyboard(self):
        p = QML_DIR / "pages" / "history" / "HistoryStatisticsPage.qml"
        if p.exists():
            content = p.read_text()
            assert "Keys.onEscapePressed" in content or "Keys.on" in content
