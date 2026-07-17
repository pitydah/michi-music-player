from unittest.mock import MagicMock
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


class TestHomeAudioBridge:
    def test_create(self):
        bridge = HomeAudioBridge(home_audio_service=MagicMock())
        assert bridge is not None
