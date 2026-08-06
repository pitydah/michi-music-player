from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import make_radio_service_mock

@pytest.fixture
def mock_stations():
    return [
        {"id": 1, "name": "Station A", "url": "http://a.stream", "codec": "MP3",
         "country": "US", "tags": ["pop"], "favorite": False, "image_path": "", "bitrate": 128},
        {"id": 2, "name": "Station B", "url": "http://b.stream", "codec": "AAC",
         "country": "UK", "tags": ["rock"], "favorite": False, "image_path": "", "bitrate": 256},
    ]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    return make_radio_service_mock(stations=mock_stations)


@pytest.fixture
def mock_player():
    return MagicMock()


class TestKeyboardNavigation:
    def test_play_then_stop(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        assert mock_player.play_url.called
        bridge.stopStream()
        assert mock_player.stop.called

    def test_toggle_favorite_then_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.toggleFavorite(1)
        assert mock_radio_mgr.favorite_station.called
        bridge.playStation("http://a.stream", "Station A")
        assert mock_player.play_url.called

    def test_edit_after_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        result = bridge.editStation(1, "Edited A", "http://edited.stream", "MP3", "US")
        assert result["ok"]

    def test_delete_after_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        bridge.refresh()
        result = bridge.deleteStation("http://a.stream")
        assert result["ok"]

    def test_play_after_stop(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        bridge.stopStream()
        bridge.playStation("http://b.stream", "Station B")
        assert mock_player.play_url.call_count >= 2

    def test_play_retry_scenario(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        bridge.stopStream()
        result = bridge.retryCurrent()
        assert result["ok"]

    def test_focus_equivalent_to_refresh(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.refresh()
        assert result["ok"]
        assert len(bridge.stations) == 2

    def test_sequential_play_different_stations(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "A")
        bridge.playStation("http://b.stream", "B")
        bridge.playStation("http://a.stream", "A")
        bridge._on_station_connection_done()
        assert len(bridge.history) >= 1

    def test_enter_equivalent_to_play(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "Station A")
        assert isinstance(bridge._current_station, str)
        assert bridge._current_station == "http://a.stream"

    def test_tab_between_sections(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        assert len(bridge.favorites) == 0

    def test_escape_equivalent_to_stop(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "A")
        bridge.cancelStream()
        assert mock_player.stop.called

    def test_play_history_retained(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://a.stream", "A")
        bridge.playStation("http://b.stream", "B")
        bridge._on_station_connection_done()
        assert len(bridge.history) >= 1

    def test_full_keyboard_workflow(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        bridge.playStation("http://a.stream", "Station A")
        assert bridge._current_station == "http://a.stream"
        bridge.stopStream()
        assert mock_player.stop.called
        bridge.playStation("http://b.stream", "Station B")
        assert bridge._current_station == "http://b.stream"
        bridge.cancelStream()
        assert mock_player.stop.called
