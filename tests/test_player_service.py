from unittest.mock import MagicMock
from audio.player_service import PlayerService


class TestPlayerService:
    def test_create(self):
        svc = PlayerService(engine=MagicMock(), event_bus=MagicMock())
        assert not svc._current_title

    def test_volume_default(self):
        svc = PlayerService(engine=MagicMock(), event_bus=MagicMock())
        svc.set_volume(50)
        assert svc._current_title == ""
