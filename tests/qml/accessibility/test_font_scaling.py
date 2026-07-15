"""Test font scaling.

Verifies:
- ThemeStore exposes fontScaleFactor and fontScale
- AccessibilityBridge exposes fontScale property
- All page text uses MichiTheme.typography.* or font.pixelSize from theme tokens
- No hardcoded pixel sizes outside theme references
"""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
PAGE_PATHS = [
    "pages/devices/DevicesPage.qml",
    "pages/home/HomePage.qml",
    "pages/home_audio/HomeAudioPage.qml",
    "pages/connections/ConnectionsPage.qml",
    "pages/library/LibraryPage.qml",
    "pages/history/HistoryPage.qml",
    "pages/playlists/PlaylistsPage.qml",
    "pages/search/GlobalSearchPage.qml",
    "pages/radio/RadioPage.qml",
    "pages/mix/MixHubPage.qml",
    "pages/assistant/AssistantPage.qml",
    "pages/audio_lab/AudioLabOverviewPage.qml",
]
pytestmark = [pytest.mark.qml_module("accessibility")]


class TestFontScalingTheme:
    def test_theme_store_has_font_scale(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "fontScale" in content, "ThemeStore lacks fontScale property"

    def test_theme_store_has_font_scale_factor(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "fontScaleFactor" in content, "ThemeStore lacks fontScaleFactor"

    def test_theme_store_font_scale_factor_logic(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "return 1.0" in content, "ThemeStore missing default scale factor"

    def test_michi_typography_has_sizes(self):
        path = QML_DIR / "theme/MichiTypography.qml"
        if not path.exists():
            pytest.skip("MichiTypography.qml not found")
        content = path.read_text()
        for size in ["heroTitleSize", "pageTitleSize", "sectionTitleSize",
                      "cardTitleSize", "bodySize", "captionSize", "metaSize", "badgeSize"]:
            assert size in content, f"MichiTypography lacks {size}"

    def test_michi_typography_has_weights(self):
        path = QML_DIR / "theme/MichiTypography.qml"
        if not path.exists():
            pytest.skip("MichiTypography.qml not found")
        content = path.read_text()
        for weight in ["weightLight", "weightNormal", "weightMedium",
                        "weightSemiBold", "weightBold"]:
            assert weight in content, f"MichiTypography lacks {weight}"


class TestFontScalingBridge:
    def test_bridge_exposes_font_scale(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert hasattr(bridge, "fontScale"), \
            "AccessibilityBridge lacks fontScale property"

    def test_theme_bridge_exposes_font_scale(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        bridge = ThemeBridge()
        assert hasattr(bridge, "fontScale"), \
            "ThemeBridge lacks fontScale property"

    def test_bridge_font_scale_default(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert bridge.fontScale in ("normal", "small", "large", "xlarge")

    def test_bridge_font_scale_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        bridge.fontScale = "large"
        assert bridge.fontScale == "large"


class TestFontScalingPages:
    def test_pages_use_theme_typography(self):
        for page_rel in PAGE_PATHS:
            path = QML_DIR / page_rel
            if not path.exists():
                continue
            content = path.read_text()
            assert "MichiTheme.typography." in content, \
                f"{page_rel} does not reference MichiTheme.typography"

    def test_pages_no_hardcoded_font_sizes(self):
        for page_rel in PAGE_PATHS:
            path = QML_DIR / page_rel
            if not path.exists():
                continue
            content = path.read_text()
            font_pixel_lines = [
                line for line in content.split("\n")
                if "font.pixelSize" in line and "MichiTheme.typography" not in line
            ]
            if font_pixel_lines:
                for line in font_pixel_lines:
                    stripped = line.strip()
                    if "font.pixelSize:" in stripped and "MichiTheme" not in stripped:
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
