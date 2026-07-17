from unittest.mock import MagicMock
from core.audio_lab.audio_conversion_service import AudioConversionService


class TestAudioConversionService:
    def test_create(self):
        svc = AudioConversionService(wm=MagicMock())
        assert svc is not None
