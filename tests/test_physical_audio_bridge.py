from unittest.mock import MagicMock
from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge


class TestPhysicalAudioBridge:
    def test_create(self):
        bridge = PhysicalAudioBridge(physical_audio_service=MagicMock())
        assert bridge is not None
