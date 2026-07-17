from unittest.mock import MagicMock
from core.audio_lab.audio_lab_job_adapter import AudioLabJobAdapter


class TestAudioLabJobAdapter:
    def test_create(self):
        adapter = AudioLabJobAdapter(wm=MagicMock())
        assert adapter is not None
