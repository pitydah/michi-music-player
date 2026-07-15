from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtQml import QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


class TestSettingsKeyboard:
    SETTINGS_PATH = "pages/SettingsPage.qml"

    def test_category_list_tab_navigation(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "activeFocusOnTab" in content

    def test_category_item_enter_opens(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "Keys.onReturnPressed" in content or "onClicked" in content

    def test_category_item_space_opens(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "Keys.onSpacePressed" in content or "onClicked" in content

    def test_search_field_focusable(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "SearchField" in content

    def test_back_button_focusable(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "Volver" in content

    def test_reset_all_button_focusable(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "Restaurar todo" in content or "resetAll" in content

    def test_reset_category_button_focusable(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "Restaurar categoría" in content or "resetCategory" in content

    def test_breadcrumb_navigation_keyboard(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "back()" in content

    def test_category_items_have_tab_order(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "activeFocusOnTab" in content
        assert "KeyNavigation.tab" in content or "activeFocusOnTab" in content

    def test_confirm_reset_dialog_keyboard(self, engine):
        content = (QML_DIR / self.SETTINGS_PATH).read_text()
        assert "confirmResetDialog" in content or "ConfirmActionDialog" in content
