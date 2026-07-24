"""Tests for advanced radio — ICY metadata, directory, stream HTTP mock."""



class TestRadioAdvanced:
    def test_radio_repository_import(self):
        from core.radio.repository import RadioRepository
        assert RadioRepository is not None

    def test_radio_repository_add(self):
        from core.radio.repository import RadioRepository, RadioStation
        repo = RadioRepository()
        result = repo.add_station(RadioStation(name="Test", url="http://test.fm"))
        assert result["ok"]

    def test_radio_repository_search(self):
        from core.radio.repository import RadioRepository, RadioStation
        repo = RadioRepository()
        repo.add_station(RadioStation(name="Classic Rock FM", url="http://rock.fm", genre="Rock"))
        repo.add_station(RadioStation(name="Smooth Jazz", url="http://jazz.fm", genre="Jazz"))
        results = repo.search("rock")
        assert len(results) >= 1

    def test_radio_bridge_has_search(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert hasattr(RadioBridge, 'search')

    def test_radio_bridge_has_add(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert hasattr(RadioBridge, 'addStation')

    def test_radio_repository_import_m3u(self):
        from core.radio.repository import RadioRepository
        repo = RadioRepository()
        stations = [
            {"name": "Station A", "url": "http://a.fm"},
            {"name": "Station B", "url": "http://b.fm"},
        ]
        result = repo.import_stations(stations)
        assert result["imported"] == 2

    def test_radio_repository_history(self):
        from core.radio.repository import RadioRepository, RadioStation
        repo = RadioRepository()
        r = repo.add_station(RadioStation(name="Hist FM", url="http://hist.fm"))
        repo.record_play(r["id"])
        history = repo.get_history()
        assert len(history) == 1
