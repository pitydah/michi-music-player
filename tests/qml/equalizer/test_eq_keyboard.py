"""Keyboard and accessibility tests for EQ QML pages."""
from pathlib import Path

import pytest

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = [pytest.mark.qml_module("eq_dsp"), pytest.mark.qml_dimension("accessibility")]

EQ_FILES = [
    "pages/EqPage.qml",
    "pages/equalizer/EqualizerPage.qml",
    "pages/equalizer/EqualizerBandControl.qml",
    "pages/equalizer/EqualizerGraph.qml",
    "pages/equalizer/EqualizerPresetBrowser.qml",
    "pages/equalizer/DSPModuleCard.qml",
    "pages/equalizer/DSPConflictWarning.qml",
    "pages/equalizer/DSPChainPage.qml",
]


class TestEqKeyboard:
    @pytest.mark.parametrize("rel_path", EQ_FILES)
    def test_has_object_names(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "objectName:" in content, f"{rel_path} lacks objectName"

    @pytest.mark.parametrize("rel_path", EQ_FILES)
    def test_has_accessible(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "Accessible." in content, f"{rel_path} lacks Accessible declarations"

    @pytest.mark.parametrize("rel_path", EQ_FILES)
    def test_has_focus_management(self, rel_path):
        p = QML_DIR / rel_path
        if not p.exists():
            pytest.skip(f"{p} not found")
        content = p.read_text()
        assert "focus:" in content or "FocusScope" in content or "activeFocus" in content, \
            f"{rel_path} lacks focus management"

    def test_eq_page_has_bypass_toggle(self):
        p = QML_DIR / "pages/EqPage.qml"
        if not p.exists():
            pytest.skip("EqPage.qml not found")
        content = p.read_text()
        assert "objectName: \"eqBypassToggle\"" in content

    def test_eq_page_has_reset_button(self):
        p = QML_DIR / "pages/EqPage.qml"
        if not p.exists():
            pytest.skip("EqPage.qml not found")
        content = p.read_text()
        assert "objectName: \"eqResetButton\"" in content

    def test_eq_page_has_preamp_slider_named(self):
        p = QML_DIR / "pages/EqPage.qml"
        if not p.exists():
            pytest.skip("EqPage.qml not found")
        content = p.read_text()
        assert "objectName: \"eqPreampSlider\"" in content

    def test_eq_page_accessible_pane(self):
        p = QML_DIR / "pages/EqPage.qml"
        if not p.exists():
            pytest.skip("EqPage.qml not found")
        content = p.read_text()
        assert "Accessible.role: Accessible.Pane" in content
        assert "Accessible.name: \"Ecualizador\"" in content

    def test_equalizer_band_control_accessible(self):
        p = QML_DIR / "pages/equalizer/EqualizerBandControl.qml"
        if not p.exists():
            pytest.skip("EqualizerBandControl.qml not found")
        content = p.read_text()
        assert "accessibleName" in content or "Accessible." in content

    def test_preset_browser_has_file_dialogs(self):
        p = QML_DIR / "pages/equalizer/EqualizerPresetBrowser.qml"
        if not p.exists():
            pytest.skip("EqualizerPresetBrowser.qml not found")
        content = p.read_text()
        assert "FileDialog" in content
        assert "importPreset" in content or "exportPreset" in content
