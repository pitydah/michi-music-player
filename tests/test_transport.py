from sync.transport import DeviceInfo, DeviceCapability, SyncTransport


class TestTransport:
    def test_device_info(self):
        info = DeviceInfo(device_id="123", name="Test Device")
        assert info.device_id == "123"

    def test_capability_enum(self):
        assert DeviceCapability.AUDIO_PLAYBACK.value == "audio_playback"
