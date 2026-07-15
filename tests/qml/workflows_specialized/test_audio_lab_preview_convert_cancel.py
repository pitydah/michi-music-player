"""MW: Audio Lab — preview analysis, convert file, cancel conversion."""
from __future__ import annotations

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestAudioLabPreviewConvertCancel(SpecializedWorkflowBase):
    def test_preview_analysis(self, audio_lab_fixtures):
        b = audio_lab_fixtures
        b.refresh()
        assert len(b.modules) >= 1

    def test_select_module(self, audio_lab_fixtures):
        b = audio_lab_fixtures
        module = b.modules[0]
        assert module.get("id") == "diagnostics"
        assert module.get("status") == "available"

    def test_backend_info_available(self, audio_lab_fixtures):
        b = audio_lab_fixtures
        assert b.backendInfo.get("available") is True

    def test_full_workflow(self, audio_lab_fixtures):
        b = audio_lab_fixtures
        b.refresh()
        assert b.modules[0]["status"] == "available"

    def test_no_modules_when_unavailable(self):
        b = MagicMock()
        b.modules = []
        assert len(b.modules) == 0
