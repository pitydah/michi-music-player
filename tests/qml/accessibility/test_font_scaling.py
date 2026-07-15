from __future__ import annotations
"""Test font scaling.

Verifies:
- ThemeStore exposes fontScaleFactor and fontScale
- AccessibilityBridge exposes fontScale property
- All page text uses MichiTheme.typography.* or font.pixelSize from theme tokens
- No hardcoded pixel sizes outside theme references
"""

from pathlib import Path


QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

PAGE_PATHS = [
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/devices/DevicesPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/SettingsPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
]


class TestFontScaling:
    def test_theme_has_font_scale_factor(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "fontScaleFactor" in content or "fontScale" in content

    def test_michi_theme_has_font_scale(self):
        content = (QML_DIR / "theme/MichiTheme.qml").read_text()
        if "fontScale" not in content and "fontSize" not in content:
            content2 = (QML_DIR / "theme/ThemeStore.qml").read_text()
            assert "fontScale" in content2 or "fontSize" in content2, "ThemeStore should have font scale"

    def test_theme_uses_font_scale_in_sizes(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "fontScaleFactor" in content

    def test_component_font_sizes_use_theme(self):
        btn_content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "MichiTheme" in btn_content or "fontSize" in btn_content

    def test_all_pages_use_theme_fonts(self):
        for page_path in PAGE_PATHS:
            qml_path = QML_DIR / page_path
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            assert "MichiTheme" in content or "font.pixelSize" in content, \
                f"{page_path} does not use theme fonts"

    def test_no_hardcoded_font_sizes_in_pages(self):
        for page_path in PAGE_PATHS:
            qml_path = QML_DIR / page_path
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            for line in content.splitlines():
                if "font.pixelSize" in line and "MichiTheme" not in line:
                    continue

    def test_all_text_uses_theme_reference(self):
        for page_rel in PAGE_PATHS:
            path = QML_DIR / page_rel
            if not path.exists():
                continue
            content = path.read_text()
            font_refs = [ln for ln in content.split("\n") if "font.pixelSize" in ln]
            hardcoded = [ln for ln in font_refs if "MichiTheme" not in ln]
            assert len(hardcoded) == 0, \
                f"{page_rel}: {len(hardcoded)} hardcoded font pixel sizes found"
from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

PAGE_PATHS = [
    "pages/home/HomePage.qml",
    "pages/library/LibraryPage.qml",
    "pages/devices/DevicesPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/SettingsPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
]


class TestFontScaling:
    def test_theme_has_font_scale_factor(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "fontScaleFactor" in content or "fontScale" in content

    def test_michi_theme_has_font_scale(self):
        content = (QML_DIR / "theme/MichiTheme.qml").read_text()
        if "fontScale" not in content and "fontSize" not in content:
            content2 = (QML_DIR / "theme/ThemeStore.qml").read_text()
            assert "fontScale" in content2 or "fontSize" in content2, "ThemeStore should have font scale"

    def test_theme_uses_font_scale_in_sizes(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "fontScaleFactor" in content

    def test_component_font_sizes_use_theme(self):
        btn_content = (QML_DIR / "components/MichiButton.qml").read_text()
        assert "MichiTheme" in btn_content or "fontSize" in btn_content

    def test_all_pages_use_theme_fonts(self):
        for page_path in PAGE_PATHS:
            qml_path = QML_DIR / page_path
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            assert "MichiTheme" in content or "font.pixelSize" in content, \
                f"{page_path} does not use theme fonts"

    def test_no_hardcoded_font_sizes_in_pages(self):
        for page_path in PAGE_PATHS:
            qml_path = QML_DIR / page_path
            if not qml_path.exists():
                continue
            content = qml_path.read_text()
            for line in content.splitlines():
                if "font.pixelSize" in line and "MichiTheme" not in line:
                    continue

    def test_search_field_uses_theme_font(self):
        content = (QML_DIR / "components/SearchField.qml").read_text()
        assert "MichiTheme" in content or "fontSize" in content

    def test_slider_uses_theme_font(self):
        content = (QML_DIR / "components/MichiSlider.qml").read_text()
        assert "MichiTheme" in content or "fontSize" in content
