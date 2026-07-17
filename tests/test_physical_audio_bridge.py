from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge


class TestPhysicalAudioBridge:
    def test_create(self):
        bridge = PhysicalAudioBridge()
        assert bridge is not None
