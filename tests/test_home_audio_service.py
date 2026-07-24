from integrations.home_audio_service import SnapcastService, HomeAssistantService


class TestHomeAudioService:
    def test_snapcast_create(self):
        svc = SnapcastService(host="localhost", port=1780)
        assert svc._host == "localhost"

    def test_home_assistant_create(self):
        svc = HomeAssistantService(host="localhost", token="test")
        assert svc._host == "localhost"
