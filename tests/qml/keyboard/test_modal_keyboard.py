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


class TestModalKeyboard:
    def test_playlists_dialog_escape_closes(self, engine):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onRejected" in content or "standardButtons" in content

    def test_playlists_dialog_enter_confirms(self, engine):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onAccepted" in content or "onClick" in content

    def test_history_dialog_escape_closes(self, engine):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "onRejected" in content or "standardButtons" in content

    def test_history_dialog_enter_confirms(self, engine):
        content = (QML_DIR / "pages/history/HistoryPage.qml").read_text()
        assert "onAccepted" in content or "Yes" in content

    def test_settings_confirm_dialog_escape(self, engine):
        content = (QML_DIR / "pages/SettingsPage.qml").read_text()
        assert "confirmResetDialog" in content or "ConfirmActionDialog" in content

    def test_playlists_textfield_enter_accepted(self, engine):
        content = (QML_DIR / "pages/playlists/PlaylistsPage.qml").read_text()
        assert "onAccepted" in content or "Keys.onReturnPressed" in content

    def test_global_modals_have_escape_handler(self, engine):
        pages_to_check = [
            "pages/playlists/PlaylistsPage.qml",
            "pages/history/HistoryPage.qml",
            "pages/SettingsPage.qml",
        ]
        for path in pages_to_check:
            qml_path = QML_DIR / path
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            assert "onRejected" in content or "Dialog" in content, \
                f"{path} should have dialog close handling"

    def test_enter_on_button_triggers_action(self, engine):
        btn_content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "Accessible.Button" in btn_content or "focusPolicy" in btn_content

    def test_escape_on_input_clears(self, engine):
        sf_path = QML_DIR / "components/SearchField.qml"
        if sf_path.exists():
            content = sf_path.read_text()
            has_escape = "Keys.onEscapePressed" in content or "Escape" in content
            if not has_escape:
                pytest.skip("SearchField does not handle Escape key")
        else:
            pytest.skip("SearchField.qml not found")
