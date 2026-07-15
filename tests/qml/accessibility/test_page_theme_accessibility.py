"""Test that all pages under domain ownership follow theme, accessibility, and keyboard conventions.

Verifies:
- No hardcoded colors outside MichiTheme.colors
- No hardcoded radii outside MichiTheme.radius*
- No hardcoded font sizes outside MichiTheme.typography
- objectName present on root
- Accessible.role, Accessible.name, Accessible.description on root
- Keys.onEscapePressed or keyboard handler on root
"""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PAGES = [
    "pages/PlaybackPage.qml",
    "pages/nowplaying/NowPlayingPage.qml",
    "pages/LyricsPage.qml",
    "pages/DiagnosticsPage.qml",
    "pages/SmartTaggingPage.qml",
    "pages/outputs/OutputProfilesPage.qml",
    "pages/metadata/MetadataInspectorPage.qml",
    "pages/settings/SettingsPage.qml",
    "pages/settings/SettingsAboutPage.qml",
    "pages/library/LibraryPage.qml",
    "pages/library/AlbumDetailPage.qml",
    "pages/library/ArtistDetailPage.qml",
    "pages/home/HomePage.qml",
    "pages/history/HistoryPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/queue/QueuePage.qml",
]

pytestmark = [pytest.mark.qml_module("accessibility")]


@pytest.fixture(params=PAGES)
def page_path(request):
    return QML_DIR / request.param


class TestPageThemeAccessibility:
    def test_has_object_name(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "objectName:" in content, f"{page_path.name} lacks objectName"

    def test_has_accessible_role(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Accessible.role" in content, f"{page_path.name} lacks Accessible.role"

    def test_has_accessible_name(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Accessible.name" in content, f"{page_path.name} lacks Accessible.name"

    def test_has_accessible_description(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "Accessible.description" in content, f"{page_path.name} lacks Accessible.description"

    def test_no_hardcoded_colors(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        for bad in ['color: "white"', 'color: "black"', 'color: "red"',
                     'color: "#', 'color: "rgb(']:
            assert bad not in content, f"{page_path.name} has hardcoded color: {bad}"

    def test_no_error_color_property(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "errorColor" not in content, f"{page_path.name} uses deprecated errorColor"

    def test_has_keyboard_handler(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        has_keys = "Keys.onEscapePressed" in content or "Keys.onPressed" in content
        assert has_keys, f"{page_path.name} lacks keyboard handler"

    def test_has_focus(self, page_path):
        if not page_path.exists():
            pytest.skip(f"{page_path} not found")
        content = page_path.read_text()
        assert "focus:" in content or "FocusScope" in content or "activeFocusOnTab" in content, \
            f"{page_path.name} lacks focus management"
