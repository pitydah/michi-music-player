from unittest.mock import MagicMock
from core.audio_lab.audio_normalization_service import AudioNormalizationService


class TestAudioNormalizationService:
    def test_create(self):
        svc = AudioNormalizationService(wm=MagicMock())
        assert svc is not None
