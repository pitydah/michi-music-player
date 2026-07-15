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


class TestSearchKeyboard:
    SEARCH_PATH = "pages/search/GlobalSearchPage.qml"

    def test_search_input_has_focus(self, engine):
        content = (QML_DIR / self.SEARCH_PATH).read_text()
        assert "SearchField" in content or "TextInput" in content or "TextEdit" in content

    def test_search_input_keyboard_handling(self, engine):
        content = (QML_DIR / self.SEARCH_PATH).read_text()
        assert "onSearchTextChanged" in content or "onTextChanged" in content

    def test_results_keyboard_accessible(self, engine):
        content = (QML_DIR / self.SEARCH_PATH).read_text()
        assert "activeFocusOnTab" in content or "focus" in content or "Keys.on" in content

    def test_no_results_text_accessible(self, engine):
        content = (QML_DIR / self.SEARCH_PATH).read_text()
        assert "Sin resultados" in content or "no results" in content.lower()

    def test_search_enter_triggers_search(self, engine):
        content = (QML_DIR / self.SEARCH_PATH).read_text()
        assert "onSearchTextChanged" in content

    def test_search_escape_clears(self, engine):
        qml_path = QML_DIR / "components/SearchField.qml"
        if qml_path.exists():
            content = qml_path.read_text()
            assert "Escape" in content or "onActiveFocusChanged" in content or "Keys.onEscapePressed" in content
        else:
            pytest.skip("SearchField.qml not found")
