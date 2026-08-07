from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import make_radio_service_mock

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_stations():
    return [
        {"id": 1, "name": "Jazz FM", "url": "http://jazz.stream", "codec": "MP3",
         "country": "US", "tags": ["jazz", "cool"], "favorite": False,
         "image_path": "", "bitrate": 128},
        {"id": 2, "name": "Rock FM", "url": "http://rock.stream", "codec": "AAC",
         "country": "UK", "tags": ["rock", "classic"], "favorite": False,
         "image_path": "", "bitrate": 256},
    ]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    return make_radio_service_mock(stations=mock_stations)


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player


class TestRadioWorkflow:

    def test_play_station(self, mock_radio_mgr, mock_player):
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

    def test_play_adds_to_history_on_confirmation(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 0
        bridge._on_station_connection_done()
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Jazz FM"

    def test_get_metadata_unavailable(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.getMetadata("http://jazz.stream")
        assert not result["ok"]
        assert result["error"] == "NO_METADATA"

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
        assert mock_radio_mgr.favorite_station.called
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert mock_player.play_url.called

    def test_full_lifecycle(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert bridge._current_station == "http://jazz.stream"
        bridge._on_station_connection_done()
        assert bridge.isPlaying is True
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
