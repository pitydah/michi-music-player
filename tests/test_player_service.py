"""Tests for PlayerService wrappers."""
import pytest
from unittest.mock import MagicMock


class TestPlayerService:
    @pytest.fixture
    def service(self):
        from audio.player_service import PlayerService
        engine = MagicMock()
        engine.state = MagicMock()
        return PlayerService(engine)

    def test_set_transmit_device(self, service):
        service.set_transmit_device(None)
        service._engine.set_transmit_device.assert_called_once_with(None)

    def test_get_transmit_device(self, service):
        service._engine.get_transmit_device.return_value = "dev1"
        result = service.get_transmit_device()
        assert result == "dev1"

    def test_set_eq_graphic(self, service):
        bands = [0.0] * 31
        service.set_eq_graphic(bands)
        service._engine.set_eq_graphic.assert_called_once_with(bands)

    def test_set_eq_parametric(self, service):
        bands = [{"type": "peaking", "frequency": 1000, "q": 0.7, "gain": 3.0}]
        service.set_eq_parametric(bands)
        service._engine.set_eq_parametric.assert_called_once_with(bands)

    def test_set_eq_bypass(self, service):
        service.set_eq_bypass(True)
        service._engine.set_eq_bypass.assert_called_once_with(True)

    def test_set_eq_preamp(self, service):
        service.set_eq_preamp(-2.0)
        service._engine.set_eq_preamp.assert_called_once_with(-2.0)

    def test_set_spectrum_enabled(self, service):
        service.set_spectrum_enabled(True)
        service._engine.set_spectrum_enabled.assert_called_once_with(True)
