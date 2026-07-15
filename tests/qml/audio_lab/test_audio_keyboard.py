"""Tests for keyboard accessibility and focus across all Audio Lab pages."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.qml_module("audio_lab")

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


AUDIO_LAB_PAGES = [
    "AudioLabOverviewPage.qml",
    "AudioConversionPage.qml",
    "AudioAnalysisPage.qml",
    "ReplayGainPage.qml",
    "AudioNormalizationPage.qml",
    "AudioIntegrityPage.qml",
    "AudioComparisonPage.qml",
    "AudioBatchJobsPage.qml",
    "AudioConversionProfileEditor.qml",
]


class TestAudioKeyboard:
    def _read(self, name: str) -> str:
        return (QML_DIR / "pages/audio_lab" / name).read_text()

    def test_all_pages_have_escape_handler(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "Keys.onEscapePressed" in source, f"{name} missing Escape handler"

    def test_all_pages_have_focus_scope(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "FocusScope" in source, f"{name} missing FocusScope"

    def test_all_pages_have_active_focus_on_tab(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "activeFocusOnTab: true" in source, f"{name} missing activeFocusOnTab"

    def test_all_pages_have_object_name(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "objectName:" in source, f"{name} missing objectName"

    def test_all_pages_have_accessible_role(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "Accessible.role" in source, f"{name} missing Accessible.role"

    def test_all_pages_have_accessible_name(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "Accessible.name" in source, f"{name} missing Accessible.name"

    def test_focus_policy_on_interactive_elements(self):
        for name in ["AudioLabOverviewPage.qml", "AudioConversionPage.qml", "ReplayGainPage.qml"]:
            source = self._read(name)
            assert "focusPolicy" in source, f"{name} missing focusPolicy"

    def test_keynav_on_cards(self):
        source = self._read("AudioLabOverviewPage.qml")
        assert "KeyNavigation" in source

    def test_enter_space_activation(self):
        for name in ["AudioLabOverviewPage.qml", "ReplayGainPage.qml"]:
            source = self._read(name)
            assert "Keys.onReturnPressed" in source or "Keys.onSpacePressed" in source, f"{name} missing Enter/Space"

    def test_michitheme_used_everywhere(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "MichiTheme" in source, f"{name} missing MichiTheme"

    def test_bridge_null_guards_everywhere(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "typeof" in source, f"{name} missing bridge null guard"

    def test_flickable_present_on_all_scrollable_pages(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "Flickable" in source, f"{name} missing Flickable"

    def test_no_emoji_in_accessible_names(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            lines = [line for line in source.split("\n") if "Accessible.name" in line]
            for line in lines:
                assert "\u2639" not in line and "\u2600" not in line, f"{name} has emoji in Accessible.name"

    def test_page_header_heading_role(self):
        for name in AUDIO_LAB_PAGES:
            source = self._read(name)
            assert "Accessible.Heading" in source, f"{name} missing Accessible.Heading"
