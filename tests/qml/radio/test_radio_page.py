"""Test RadioPage integration with RadioBridge for station listing and search."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = [pytest.mark.qml_module("radio")]


@pytest.fixture
def mock_stations():
    stations = []
    for i, (name, url, codec, country, fav) in enumerate([
        ("Jazz FM", "http://jazz.stream", "MP3", "US", True),
        ("Rock FM", "http://rock.stream", "AAC", "UK", False),
        ("Classical", "http://classical.stream", "MP3", "DE", False),
        ("News Talk", "http://news.stream", "AAC", "US", True),
        ("Latin Beats", "http://latin.stream", "MP3", "MX", False),
    ]):
        s = MagicMock()
        s.id = i + 1
        s.name = name
        s.url = url
        s.codec = codec
        s.country = country
        s.tags = []
        s.favorite = fav
        s.bitrate = 128 + i * 32
        stations.append(s)
    return stations


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player


@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestRadioPage:
    """Test radio page data flow and station management."""

    def test_refresh_stations(self, bridge):
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] == 5
        assert len(bridge.stations) == 5

    def test_favorites_filtered(self, bridge):
        bridge.refresh()
        assert len(bridge.favorites) == 2
        assert bridge.favorites[0]["name"] == "Jazz FM"
        assert bridge.favorites[1]["name"] == "News Talk"

    def test_search_by_name(self, bridge):
        bridge.refresh()
        result = bridge.search(query="Jazz")
        assert result["ok"]
        assert result["count"] >= 1
        assert any(r["name"] == "Jazz FM" for r in result["results"])

    def test_search_by_country(self, bridge):
        bridge.refresh()
        result = bridge.search(country="UK")
        assert result["ok"]
        assert any(r["country"] == "UK" for r in result["results"])

    def test_search_no_results(self, bridge):
        bridge.refresh()
        result = bridge.search(query="zzzznonexistent")
        assert result["ok"]
        assert result["count"] == 0

    def test_search_empty_query(self, bridge):
        bridge.refresh()
        result = bridge.search(query="")
        assert result["ok"]
        assert result["count"] == 5

    def test_station_favorite_toggle(self, bridge):
        bridge.refresh()
        result = bridge.toggleFavorite(1)
        assert result["ok"]
        assert result["favorite"] is True

    def test_play_station(self, bridge, mock_player):
        result = bridge.playStation("http://test.stream")
        assert result["ok"]
        mock_player.play_url.assert_called_once_with("http://test.stream")

    def test_stop_stream(self, bridge, mock_player):
        result = bridge.stopStream()
        assert result["ok"]
        mock_player.stop.assert_called_once()

    def test_empty_stations_list(self):
        mgr = MagicMock()
        mgr.get_all.return_value = []
        b = RadioBridge(radio_manager=mgr, player_service=MagicMock())
        b.refresh()
        assert len(b.stations) == 0

    def test_stations_ordered(self, bridge):
        bridge.refresh()
        names = [s["name"] for s in bridge.stations]
        assert names == ["Jazz FM", "Rock FM", "Classical", "News Talk", "Latin Beats"]
