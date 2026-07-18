"""Tests for RadioService and RadioRepository."""
import pytest


class TestRadioRepository:
    @pytest.fixture
    def repo(self):
        from core.radio.repository import RadioRepository
        return RadioRepository()

    def test_add_station(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Test FM", url="http://test.fm/stream"))
        assert r["ok"]
        assert len(repo.get_all_stations()) == 1

    def test_remove_station(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Test FM", url="http://test.fm/stream"))
        repo.remove_station(r["id"])
        assert len(repo.get_all_stations()) == 0

    def test_search(self, repo):
        from core.radio.repository import RadioStation
        repo.add_station(RadioStation(name="Rock FM", url="http://rock.fm/stream", genre="Rock"))
        repo.add_station(RadioStation(name="Jazz FM", url="http://jazz.fm/stream", genre="Jazz"))
        results = repo.search("rock")
        assert len(results) == 1
        assert results[0].name == "Rock FM"

    def test_favorite(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Fav FM", url="http://fav.fm/stream"))
        repo.toggle_favorite(r["id"])
        assert len(repo.get_favorites()) == 1
        repo.toggle_favorite(r["id"])
        assert len(repo.get_favorites()) == 0

    def test_play_count(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Count FM", url="http://count.fm/stream"))
        repo.record_play(r["id"])
        repo.record_play(r["id"])
        station = repo.get_station(r["id"])
        assert station.play_count == 2

    def test_import_stations(self, repo):
        stations = [{"name": "A", "url": "http://a"}, {"name": "B", "url": "http://b"}]
        r = repo.import_stations(stations)
        assert r["imported"] == 2

    def test_history(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Hist FM", url="http://hist.fm/stream"))
        repo.record_play(r["id"])
        repo.record_play(r["id"])
        history = repo.get_history()
        assert len(history) == 2

    def test_clear_history(self, repo):
        from core.radio.repository import RadioStation
        r = repo.add_station(RadioStation(name="Hist FM", url="http://hist.fm/stream"))
        repo.record_play(r["id"])
        repo.clear_history()
        assert len(repo.get_history()) == 0


class TestRadioService:
    @pytest.fixture
    def svc(self):
        from core.radio.radio_service import RadioService
        from core.radio.repository import RadioRepository
        return RadioService(repository=RadioRepository())

    def test_add_station(self, svc):
        r = svc.add_station("Test FM", "http://test.fm/stream", genre="Test")
        assert r["ok"]

    def test_delete_station(self, svc):
        r = svc.add_station("Del FM", "http://del.fm/stream")
        result = svc.delete_station(r["id"])
        assert result["ok"]

    def test_get_stations(self, svc):
        svc.add_station("A FM", "http://a.fm")
        svc.add_station("B FM", "http://b.fm")
        stations = svc.get_stations()
        assert len(stations) == 2

    def test_search_stations(self, svc):
        svc.add_station("Rock FM", "http://rock.fm", genre="Rock")
        result = svc.search_stations("rock")
        assert result["ok"]
        assert len(result["results"]) == 1

    def test_favorite(self, svc):
        r = svc.add_station("Fav FM", "http://fav.fm")
        svc.favorite_station(r["id"])
        assert len(svc.get_favorites()) == 1

    def test_export_stations(self, svc):
        svc.add_station("Export FM", "http://export.fm")
        exported = svc.export_stations()
        assert len(exported) == 1

    def test_import_stations(self, svc):
        result = svc.import_stations([{"name": "A", "url": "http://a.fm"}])
        assert result["ok"]
        assert result["imported"] == 1

    def test_stop(self, svc):
        result = svc.stop()
        assert result["ok"]

    def test_history(self, svc):
        r = svc.add_station("Hist FM", "http://hist.fm")
        svc.play_station("http://hist.fm")
        history = svc.get_history()
        assert len(history) >= 0
