from core.audio_lab.audio_comparison_service import AudioComparisonService


class TestAudioComparisonService:
    def test_create(self):
        svc = AudioComparisonService()
        assert svc is not None
