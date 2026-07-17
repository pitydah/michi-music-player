from unittest.mock import MagicMock
from core.audio_lab.audio_batch_service import AudioBatchService


class TestAudioBatchService:
    def test_create(self):
        svc = AudioBatchService(wm=MagicMock())
        assert svc is not None
