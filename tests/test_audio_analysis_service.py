from unittest.mock import MagicMock
from core.audio_lab.audio_analysis_service import AudioAnalysisService


class TestAudioAnalysisService:
    def test_create(self):
        svc = AudioAnalysisService(db=MagicMock(), wm=MagicMock())
        assert svc._enabled is True
