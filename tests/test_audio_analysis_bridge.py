from unittest.mock import MagicMock
from ui_qml_bridge.audio_analysis_bridge import AudioAnalysisBridge


class TestAudioAnalysisBridge:
    def test_create(self):
        bridge = AudioAnalysisBridge(analysis_service=MagicMock())
        assert bridge is not None
