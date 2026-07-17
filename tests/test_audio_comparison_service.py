from unittest.mock import MagicMock
from core.audio_lab.audio_comparison_service import AudioComparisonService


class TestAudioComparisonService:
    def test_create(self):
        svc = AudioComparisonService(probe_service=MagicMock())
        assert svc is not None
