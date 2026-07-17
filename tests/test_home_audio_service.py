from unittest.mock import MagicMock, patch
from integrations.home_audio_service import SnapcastService, HomeAssistantService, HomeAudioError


class TestHomeAudioService:
    def test_snapcast_create(self):
        svc = SnapcastService(host="localhost", port=1780)
        assert svc._host == "localhost"

    def test_home_assistant_create(self):
        svc = HomeAssistantService(url="http://localhost:8123", token="test")
        assert svc._url == "http://localhost:8123"
