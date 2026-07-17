from unittest.mock import MagicMock
from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


class TestAudioLabBridge:
    def test_create(self):
        bridge = AudioLabBridge()
        assert bridge is not None
