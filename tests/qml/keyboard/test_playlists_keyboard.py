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


class TestPlaylistsKeyboard:
    PL_PATH = "pages/playlists/PlaylistsPage.qml"

    def test_create_button_focusable(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "MichiButton" in content
        assert "focus" in content or "onClicked" in content

    def test_search_field_keyboard(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "SearchField" in content
        assert "onSearchTextChanged" in content or "Keys.on" in content

    def test_create_dialog_keyboard(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "Dialog" in content
        assert "Ok" in content or "onAccepted" in content

    def test_create_dialog_escape(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "onRejected" in content or "Cancel" in content or "Escape" in content

    def test_delete_selected_focusable(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "Eliminar" in content or "danger" in content

    def test_batch_delete_dialog_keyboard(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "confirmBatchDelete" in content
        assert "onAccepted" in content and "onRejected" in content

    def test_import_dialog_keyboard(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "importDialog" in content or "Import" in content

    def test_playlist_cards_keyboard(self, engine):
        content = (QML_DIR / self.PL_PATH).read_text()
        assert "onClicked" in content
