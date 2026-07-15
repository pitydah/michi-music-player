"""Keyboard and accessibility tests for Output Profiles QML pages."""
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = [pytest.mark.qml_module("output_profiles"), pytest.mark.qml_dimension("accessibility")]

OUTPUT_FILES = [
    "pages/OutputProfilesPage.qml",
    "pages/outputs/OutputProfileCard.qml",
    "pages/outputs/OutputProfileDetail.qml",
    "pages/outputs/OutputProfileEditor.qml",
    "pages/outputs/OutputCapabilityView.qml",
    "pages/outputs/OutputTestResult.qml",
]


class TestOutputProfilesKeyboard:
    @pytest.mark.parametrize("rel_path", OUTPUT_FILES)
    def test_has_object_names(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "objectName:" in content, f"{rel_path} lacks objectName"

    @pytest.mark.parametrize("rel_path", OUTPUT_FILES)
    def test_has_accessible(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "Accessible." in content, f"{rel_path} lacks Accessible declarations"

    @pytest.mark.parametrize("rel_path", OUTPUT_FILES)
    def test_has_focus_management(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "focus:" in content or "FocusScope" in content or "activeFocus" in content, \
            f"{rel_path} lacks focus management"

    def test_output_profiles_page_accessible_pane(self):
        p = QML_DIR / "pages/OutputProfilesPage.qml"
        if not p.exists():
            pytest.skip("OutputProfilesPage.qml not found")
        content = p.read_text()
        assert "Accessible.role: Accessible.Pane" in content
        assert "Accessible.name" in content

    def test_output_profiles_page_has_create_button(self):
        p = QML_DIR / "pages/OutputProfilesPage.qml"
        if not p.exists():
            pytest.skip("OutputProfilesPage.qml not found")
        content = p.read_text()
        assert "objectName: \"outputCreateProfileButton\"" in content

    def test_output_profiles_page_has_refresh_button(self):
        p = QML_DIR / "pages/OutputProfilesPage.qml"
        if not p.exists():
            pytest.skip("OutputProfilesPage.qml not found")
        content = p.read_text()
        assert "objectName: \"outputRefreshButton\"" in content

    def test_output_profile_editor_has_save_cancel(self):
        p = QML_DIR / "pages/outputs/OutputProfileEditor.qml"
        if not p.exists():
            pytest.skip("OutputProfileEditor.qml not found")
        content = p.read_text()
        assert "MichiButton" in content
        assert "Guardar" in content or "Cancelar" in content

    def test_output_profile_card_has_edit_duplicate_delete(self):
        p = QML_DIR / "pages/outputs/OutputProfileCard.qml"
        if not p.exists():
            pytest.skip("OutputProfileCard.qml not found")
        content = p.read_text()
        assert "Editar" in content
        assert "Duplicar" in content
        assert "Eliminar" in content
