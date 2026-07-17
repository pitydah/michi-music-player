from unittest.mock import MagicMock
from core.audio_lab.audio_probe_service import AudioProbeService


class TestAudioProbeService:
    def test_create(self):
        svc = AudioProbeService()
        assert svc is not None
