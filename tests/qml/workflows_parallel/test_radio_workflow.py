"""Full workflow: select station, play, metadata, reconnect, stop."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_stations():
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Jazz FM"
    s1.url = "http://jazz.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["jazz", "cool"]
    s1.favorite = False
    s1.bitrate = 128
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Rock FM"
    s2.url = "http://rock.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock", "classic"]
    s2.favorite = False
    s2.bitrate = 256
    return [s1, s2]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    mgr.remove_station.return_value = True
    mgr.get_metadata.return_value = {
        "ok": True, "title": "Take Five", "artist": "Dave Brubeck"
    }
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player


class TestFullRadioWorkflow:
    def test_select_station_and_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"]
        assert mock_player.play_url.called

    def test_play_updates_current_station(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert bridge._current_station == "http://jazz.stream"

    def test_play_adds_to_history(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Jazz FM"

    def test_get_metadata_after_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.getMetadata("http://jazz.stream")
        assert result["ok"]
        assert result["title"] == "Take Five"
        assert result["artist"] == "Dave Brubeck"

    def test_reconnect_after_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert mock_player.play_url.called
        mock_player.play_url.reset_mock()
        result = bridge.reconnectLast()
        assert result["ok"]
        assert mock_player.play_url.called

    def test_stop_after_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge.stopStream()
        assert mock_player.stop.called

    def test_stop_then_play_again(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge.stopStream()
        bridge.playStation("http://rock.stream", "Rock FM")
        assert mock_player.play_url.call_count >= 2

    def test_play_multiple_stations(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge.playStation("http://rock.stream", "Rock FM")
        assert bridge._current_station == "http://rock.stream"

    def test_favorite_then_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.toggleFavorite(1)
        assert mock_radio_mgr.toggle_favorite.called
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert mock_player.play_url.called

    def test_full_lifecycle(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert bridge._current_station == "http://jazz.stream"
        meta = bridge.getMetadata("http://jazz.stream")
        assert meta["ok"]
        bridge.reconnectLast()
        assert mock_player.play_url.called
        bridge.stopStream()
        assert mock_player.stop.called

    def test_workflow_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        bridge.refresh()
        assert bridge.stations == []
        result = bridge.playStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"
        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"
        result = bridge.stopStream()
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER"
