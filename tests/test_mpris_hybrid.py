"""Tests for MPRIS adapter with hybrid backend support."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def _patch_dbus():
    """Mock dbus to avoid session bus dependency."""
    with patch("adapters.mpris.dbus") as mock_dbus:
        mock_dbus.service.Object = MagicMock()
        mock_dbus.service.BusName = MagicMock()
        mock_dbus.SessionBus = MagicMock()
        mock_dbus.ObjectPath = MagicMock(return_value="/michi/test")
        mock_dbus.Array = MagicMock(side_effect=lambda x, **kw: x)
        mock_dbus.Int64 = MagicMock(side_effect=lambda x: x)
        mock_dbus.Dictionary = MagicMock(side_effect=lambda x, **kw: x)
        yield


class TestMPRISObjectHybrid:
    @pytest.fixture
    def mpris_obj(self):
        """Create a partial mock MPRISObject with player_service."""
        from adapters.mpris import MPRISObject

        class FakeBusName:
            def __init__(self, *a, **kw): pass
            def __hash__(self): return hash(type(self))

        obj = object.__new__(MPRISObject)
        # Manually init minimal attrs
        obj._engine = None
        obj._metadata = {}
        obj._volume = 0.7
        obj._player_service = None
        return obj

    def test_get_status_no_engine_no_service(self, mpris_obj):
        status = mpris_obj._get_status()
        assert status == "Stopped"

    def test_get_status_via_engine(self, mpris_obj):
        from audio.player import PlaybackState
        engine = MagicMock()
        engine.state = PlaybackState.PLAYING
        mpris_obj._engine = engine
        status = mpris_obj._get_status()
        assert status == "Playing"

    def test_get_status_via_player_service(self, mpris_obj):
        ps = MagicMock()
        ps.state = "playing"
        mpris_obj._player_service = ps
        status = mpris_obj._get_status()
        assert status == "Playing"

    def test_get_status_player_service_paused(self, mpris_obj):
        ps = MagicMock()
        ps.state = "paused"
        mpris_obj._player_service = ps
        status = mpris_obj._get_status()
        assert status == "Paused"

    def test_get_status_player_service_stopped(self, mpris_obj):
        ps = MagicMock()
        ps.state = "stopped"
        mpris_obj._player_service = ps
        status = mpris_obj._get_status()
        assert status == "Stopped"

    def test_set_player_service(self, mpris_obj):
        ps = MagicMock()
        mpris_obj.set_player_service(ps)
        assert mpris_obj._player_service is ps

    def test_set_engine(self, mpris_obj):
        engine = MagicMock()
        mpris_obj.set_engine(engine)
        assert mpris_obj._engine is engine

    def test_player_api_returns_ps_first(self, mpris_obj):
        """_player_api should return PlayerService when set, even if engine exists."""
        ps = MagicMock()
        engine = MagicMock()
        mpris_obj._player_service = ps
        mpris_obj._engine = engine
        api = mpris_obj._player_api()
        assert api is ps

    def test_player_api_falls_back_to_engine(self, mpris_obj):
        engine = MagicMock()
        mpris_obj._engine = engine
        api = mpris_obj._player_api()
        assert api is engine

    def test_player_api_returns_none(self, mpris_obj):
        api = mpris_obj._player_api()
        assert api is None
