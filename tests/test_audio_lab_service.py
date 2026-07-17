from unittest.mock import MagicMock
from core.audio_lab.audio_lab_service import AudioLabService


class TestAudioLabService:
    def test_create(self):
        svc = AudioLabService(db=MagicMock(), worker_manager=MagicMock())
        assert svc._db is not None
