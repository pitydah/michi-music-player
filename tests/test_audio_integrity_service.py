from unittest.mock import MagicMock
from core.audio_lab.audio_integrity_service import AudioIntegrityService


class TestAudioIntegrityService:
    def test_create(self):
        svc = AudioIntegrityService(wm=MagicMock())
        assert svc is not None
