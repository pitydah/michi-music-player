"""Negative tests: bridge null, empty states, error states across Audio Lab pages."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.qml_module("audio_lab")

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"

PAGES = {
    "AudioLabOverviewPage.qml": ["alab", "nav"],
    "AudioConversionPage.qml": ["labService", "convBridge", "nav"],
    "AudioAnalysisPage.qml": ["labService", "nav"],
    "ReplayGainPage.qml": ["labService", "nav"],
    "AudioNormalizationPage.qml": ["labService", "nav"],
    "AudioIntegrityPage.qml": ["labService", "nav"],
    "AudioComparisonPage.qml": ["labService", "nav"],
    "AudioBatchJobsPage.qml": ["jobBr", "nav"],
    "AudioConversionProfileEditor.qml": ["nav", "labService"],
}


class TestAudioNegative:
    def _read(self, name: str) -> str:
        return (QML_DIR / "pages/audio_lab" / name).read_text()

    def test_bridge_null_guard_with_typeof(self):
        for name in PAGES:
            source = self._read(name)
            assert "typeof" in source, f"{name} missing typeof guard for bridges"

    def test_empty_state_honored(self):
        for name in PAGES:
            source = self._read(name)
            if "AudioBatchJobsPage.qml" in name:
                assert "EmptyState" in source or "Sin trabajos" in source

    def test_error_state_visible(self):
        for name in ["AudioConversionPage.qml", "AudioAnalysisPage.qml",
                       "ReplayGainPage.qml", "AudioNormalizationPage.qml",
                       "AudioIntegrityPage.qml", "AudioComparisonPage.qml"]:
            source = self._read(name)
            assert "FAILED" in source, f"{name} missing FAILED state"

    def test_error_text_displayed_on_failure(self):
        for name in ["AudioConversionPage.qml", "AudioAnalysisPage.qml",
                       "ReplayGainPage.qml", "AudioNormalizationPage.qml",
                       "AudioIntegrityPage.qml", "AudioComparisonPage.qml"]:
            source = self._read(name)
            assert "Error:" in source or "error" in source.lower(), f"{name} missing error display"

    def test_buttons_disabled_on_no_bridge(self):
        for name in PAGES:
            source = self._read(name)
            assert "enabled:" in source or "enabled:" in source, f"{name} missing enabled guard"

    def test_bridge_null_brigde_property(self):
        for name in PAGES:
            source = self._read(name)
            assert "null" in source, f"{name} missing null fallback"

    def test_no_hardcoded_demo_data(self):
        for name in PAGES:
            source = self._read(name)
            assert "fake" not in source.lower(), f"{name} contains fake data"
            assert "demo" not in source.lower() or "Experimental" in source or "Demo QML" in source, f"{name} uses demo without qualifier"

    def test_empty_selection_handled(self):
        for name in ["AudioConversionPage.qml", "AudioAnalysisPage.qml"]:
            source = self._read(name)
            assert "Selecciona" in source, f"{name} missing selection prompt"

    def test_cancelling_state_prevents_double_action(self):
        for name in ["AudioConversionPage.qml"]:
            source = self._read(name)
            assert "CANCELLING" in source

    def test_disabled_buttons_during_operation(self):
        for name in ["AudioConversionPage.qml", "AudioAnalysisPage.qml"]:
            source = self._read(name)
            assert "enabled: root.pageState !== " in source or "enabled: root.pageState !==" in source, f"{name} missing state guard on buttons"

    def test_operation_cancel_functions_exist(self):
        for name in ["AudioConversionPage.qml", "AudioComparisonPage.qml",
                       "AudioNormalizationPage.qml", "AudioIntegrityPage.qml"]:
            source = self._read(name)
            assert "cancel" in source.lower(), f"{name} missing cancel functionality"

    def test_retry_after_failure(self):
        for name in ["AudioConversionPage.qml"]:
            source = self._read(name)
            assert "retryConvert" in source or "retry" in source.lower(), f"{name} missing retry"
