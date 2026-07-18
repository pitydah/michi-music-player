"""Tests for Radio — CRUD, repository, bridge."""
import pytest


class TestRadioIntegration:
    def test_radio_service_crud(self):
        from core.radio.radio_service import RadioService
        from core.radio.repository import RadioRepository
        svc = RadioService(repository=RadioRepository())
        svc.add_station("Test FM", "http://test.fm", genre="Test")
        stations = svc.get_stations()
        assert len(stations) == 1
        sid = stations[0]["id"]
        result = svc.delete_station(sid)
        assert result["ok"]

    def test_radio_favorites(self):
        from core.radio.radio_service import RadioService
        from core.radio.repository import RadioRepository
        svc = RadioService(repository=RadioRepository())
        r = svc.add_station("Fav FM", "http://fav.fm")
        svc.favorite_station(r["id"])
        assert len(svc.get_favorites()) == 1

    def test_radio_search(self):
        from core.radio.radio_service import RadioService
        from core.radio.repository import RadioRepository
        svc = RadioService(repository=RadioRepository())
        svc.add_station("Classic Rock", "http://rock.fm", genre="Rock")
        svc.add_station("Smooth Jazz", "http://jazz.fm", genre="Jazz")
        result = svc.search_stations("rock")
        assert result["ok"]
        assert len(result["results"]) == 1

    def test_radio_bridge_has_crud(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert hasattr(RadioBridge, 'addStation')
        assert hasattr(RadioBridge, 'removeStation')
        assert hasattr(RadioBridge, 'search')
        assert hasattr(RadioBridge, 'toggleFavorite')

    def test_radio_service_available(self):
        from core.composition.infrastructure import build as infra
        from core.composition.ecosystem import build as eco
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        eco(c)
        rs = c.get("radio_service")
        assert rs is not None
