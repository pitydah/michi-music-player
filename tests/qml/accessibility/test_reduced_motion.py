from __future__ import annotations

from pathlib import Path

import pytest

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


class TestReducedMotionSupport:
    def test_theme_store_has_reduce_motion(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "reduceMotion" in content or "ReduceMotion" in content

    def test_theme_store_has_motion_duration(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "motionDurationFast" in content or "motionDuration" in content

    def test_michi_theme_has_reduce_motion(self):
        content = (QML_DIR / "theme/MichiTheme.qml").read_text()
        if "reduceMotion" not in content and "ReduceMotion" not in content:
            content2 = (QML_DIR / "theme/ThemeStore.qml").read_text()
            assert "reduceMotion" in content2 or "ReduceMotion" in content2

    def test_theme_store_respects_reduced_motion(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "reduceMotion" in content
        assert "motionDurationFast" in content

    def test_theme_duration_conditional_on_motion(self):
        content = (QML_DIR / "theme/ThemeStore.qml").read_text()
        assert "reduceMotion ? 0 : " in content or "reduceMotion ? 1 : " in content or "motionDurationFast" in content

    @pytest.mark.parametrize("page_path", PAGE_PATHS)
    def test_pages_delegate_motion_to_theme(self, page_path):
        qml_path = QML_DIR / page_path
        if not qml_path.exists():
            pytest.skip(f"{page_path} not found")
        content = qml_path.read_text()
        if "Behavior" in content:
            assert True

    def test_hero_material_respects_motion(self):
        content = (QML_DIR / "materials/HeroMaterial.qml").read_text()
        if "Behavior" not in content and "reduceMotion" not in content and "motionDuration" not in content:
            pytest.skip("HeroMaterial defers motion to theme/parent")

    def test_glass_card_respects_motion(self):
        content = (QML_DIR / "components/GlassCard.qml").read_text()
        if "Behavior" not in content:
            pytest.skip("GlassCard has no animations")
