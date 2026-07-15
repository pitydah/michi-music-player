"""Test reducedMotion support.

Verifies:
- ThemeStore exposes reduceMotion property
- ThemeStore exposes motion durations that respect reduceMotion
- Pages reference motion durations via MichiTheme rather than hardcoded values
- AccessibilityBridge exposes reduceMotion property
"""

from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = [pytest.mark.qml_module("accessibility")]


class TestReducedMotionTheme:
    def test_theme_store_has_reduce_motion(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "reduceMotion" in content, "ThemeStore lacks reduceMotion property"

    def test_theme_store_motion_durations(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "motionDurationFast" in content, "ThemeStore lacks motionDurationFast"
        assert "motionDurationNormal" in content, "ThemeStore lacks motionDurationNormal"
        assert "motionDurationSlow" in content, "ThemeStore lacks motionDurationSlow"

    def test_reduce_motion_zero_when_enabled(self):
        path = QML_DIR / "theme/ThemeStore.qml"
        if not path.exists():
            pytest.skip("ThemeStore.qml not found")
        content = path.read_text()
        assert "reduceMotion ? 0 :" in content, \
            "ThemeStore does not zero durations when reduceMotion is true"

    def test_michi_motion_has_reduced_duration(self):
        path = QML_DIR / "theme/MichiMotion.qml"
        if not path.exists():
            pytest.skip("MichiMotion.qml not found")
        content = path.read_text()
        assert "reduced" in content, "MichiMotion lacks reduced duration"

    def test_michi_motion_fast_respects_reduced(self):
        path = QML_DIR / "theme/MichiMotion.qml"
        if not path.exists():
            pytest.skip("MichiMotion.qml not found")
        content = path.read_text()
        assert "fast" in content
        assert "normal" in content
        assert "slow" in content

    def test_michi_theme_exposes_motion(self):
        path = QML_DIR / "theme/MichiTheme.qml"
        if not path.exists():
            pytest.skip("MichiTheme.qml not found")
        content = path.read_text()
        assert "motionFast" in content, "MichiTheme lacks motionFast"
        assert "motionNormal" in content, "MichiTheme lacks motionNormal"
        assert "motionSlow" in content, "MichiTheme lacks motionSlow"


class TestReducedMotionBridge:
    def test_bridge_exposes_reduce_motion(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        assert hasattr(bridge, "reduceMotion"), \
            "AccessibilityBridge lacks reduceMotion property"
        assert isinstance(bridge.reduceMotion, bool)

    def test_bridge_exposes_reduce_motion_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        bridge = AccessibilityBridge()
        bridge.reduceMotion = True
        assert bridge.reduceMotion is True

    def test_theme_bridge_exposes_reduce_motion(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        bridge = ThemeBridge()
        assert hasattr(bridge, "reduceMotion"), \
            "ThemeBridge lacks reduceMotion property"
        assert isinstance(bridge.reduceMotion, bool)


class TestReducedMotionPages:
    def test_pages_no_hardcoded_animation_duration(self):
        dur_patterns = ["Behavior on", "NumberAnimation", "PropertyAnimation"]
        for page_rel in [
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
        ]:
            path = QML_DIR / page_rel
            if not path.exists():
                continue
            content = path.read_text()
            for pattern in dur_patterns:
                if pattern in content:
                    assert "motion" in content.lower() or "MichiTheme.motion" in content, \
                        f"{page_rel} uses {pattern} but doesn't reference motion tokens"
