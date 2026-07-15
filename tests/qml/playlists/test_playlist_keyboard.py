"""Tests keyboard navigation, focus, and accessibility for Playlists QML pages."""
import pytest
from pathlib import Path

pytestmark = [pytest.mark.qml_module("playlists")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PLAYLIST_FILES = [
    "PlaylistsPage.qml",
    "PlaylistDetailPage.qml",
    "PlaylistCard.qml",
    "PlaylistTrackList.qml",
    "PlaylistEditorDialog.qml",
    "PlaylistImportDialog.qml",
    "PlaylistExportDialog.qml",
    "SmartPlaylistEditor.qml",
    "SmartPlaylistEditorPage.qml",
]


class TestPlaylistKeyboard:

    @pytest.fixture(params=PLAYLIST_FILES)
    def qml_file(self, request):
        p = QML_DIR / "pages" / "playlists" / request.param
        return p

    def test_file_has_focus_scope_or_keys(self, qml_file):
        if not qml_file.exists():
            pytest.skip(f"{qml_file} not found")
        content = qml_file.read_text()
        has_focus = "FocusScope" in content or "Keys.on" in content or "activeFocusOnTab" in content
        assert has_focus, f"{qml_file.name} lacks focus handling"

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

    def test_playlists_page_focus_scope(self):
        p = QML_DIR / "pages" / "playlists" / "PlaylistsPage.qml"
        content = p.read_text()
        assert "FocusScope" in content
        assert "activeFocusOnTab" in content

    def test_detail_page_keyboard(self):
        p = QML_DIR / "pages" / "playlists" / "PlaylistDetailPage.qml"
        content = p.read_text()
        assert "Keys.onEscapePressed" in content

    def test_editor_dialog_focus_trap(self):
        p = QML_DIR / "pages" / "playlists" / "PlaylistEditorDialog.qml"
        if p.exists():
            content = p.read_text()
            assert "FocusScope" in content

    def test_import_dialog_focus_trap(self):
        p = QML_DIR / "pages" / "playlists" / "PlaylistImportDialog.qml"
        if p.exists():
            content = p.read_text()
            assert "FocusScope" in content

    def test_export_dialog_focus_trap(self):
        p = QML_DIR / "pages" / "playlists" / "PlaylistExportDialog.qml"
        if p.exists():
            content = p.read_text()
            assert "FocusScope" in content

    def test_smart_editor_page_keys(self):
        p = QML_DIR / "pages" / "playlists" / "SmartPlaylistEditorPage.qml"
        if p.exists():
            content = p.read_text()
            assert "Keys.onEscapePressed" in content
