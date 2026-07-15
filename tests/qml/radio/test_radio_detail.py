"""Test RadioStationDetailPage states and metadata display."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("detail")]


@pytest.fixture
def mock_stations():
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Jazz FM"
    s1.url = "http://jazz.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["jazz", "cool"]
    s1.favorite = True
    s1.bitrate = 128
    s1.language = "English"
    s1.genre = "Jazz"
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Rock FM"
    s2.url = "http://rock.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock", "classic"]
    s2.favorite = False
    s2.bitrate = 256
    s2.language = "English"
    s2.genre = "Rock"
    return [s1, s2]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.get_metadata.return_value = {"ok": True, "title": "Now Playing", "artist": "Artist"}
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    return player


@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestRadioDetail:
    """Test station detail display and metadata."""

    def test_station_data_structure(self, bridge):
        bridge.refresh()
        station = bridge.stations[0]
        assert station["name"] == "Jazz FM"
        assert station["url"] == "http://jazz.stream"
        assert station["codec"] == "MP3"
        assert station["country"] == "US"
        assert station["favorite"] is True

    def test_station_has_id(self, bridge):
        bridge.refresh()
        for s in bridge.stations:
            assert s["id"] > 0

    def test_favorite_state_display(self, bridge):
        bridge.refresh()
        favs = [s for s in bridge.stations if s["favorite"]]
        assert len(favs) == 1
        assert favs[0]["name"] == "Jazz FM"

    def test_play_then_stop(self, bridge, mock_player):
        play_result = bridge.playStation("http://test.stream")
        assert play_result["ok"]
        mock_player.play_url.assert_called_once()
        stop_result = bridge.stopStream()
        assert stop_result["ok"]

    def test_reconnect_last(self, bridge, mock_player):
        bridge.playStation("http://last.stream", "Last Station")
        result = bridge.reconnectLast()
        assert result["ok"]

    def test_reconnect_without_last(self, bridge):
        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"

    def test_retry_current(self, bridge, mock_player):
        bridge.playStation("http://retry.stream")
        result = bridge.retryCurrent()
        assert result["ok"]

    def test_get_station_metadata(self, bridge, mock_radio_mgr):
        result = bridge.getMetadata("http://jazz.stream")
        assert result["ok"]
        assert result.get("title") == "Now Playing"

    def test_null_player_play(self, mock_radio_mgr):
        b = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = b.playStation("http://test.stream")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

    def test_null_player_stop(self, mock_radio_mgr):
        b = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = b.stopStream()
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER"

    def test_null_manager_toggle_favorite(self):
        b = RadioBridge(radio_manager=None, player_service=MagicMock())
        result = b.toggleFavorite(1)
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"
