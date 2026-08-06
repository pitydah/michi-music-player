"""Test radio station workflows through RadioBridge."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import station_dicts, make_radio_service_mock
pytestmark = [pytest.mark.qml_module("radio")]


@pytest.fixture
def mock_stations():
    return station_dicts()


@pytest.fixture
def mock_radio_mgr(mock_stations):
    return make_radio_service_mock(stations=mock_stations)


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    return player


def test_refresh_stations(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.refresh()
    assert result["ok"]
    assert result["count"] == 2
    assert len(bridge.stations) == 2


def test_favorites_populated(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    assert len(bridge.favorites) == 1
    assert bridge.favorites[0]["name"] == "Jazz FM"


def test_add_station(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.addStation("New Station", "http://new.stream", "MP3", "DE")
    assert result["ok"]
    mock_radio_mgr.add_station.assert_called_once()


def test_add_station_empty_url(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.addStation("Test", "", "MP3", "")
    assert not result["ok"]
    assert result["error"] == "EMPTY_URL"


def test_play_station(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("http://stream.url")
    assert result["ok"]
    mock_player.play_url.assert_called_once_with("http://stream.url")


def test_play_station_empty_url(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("")
    assert not result["ok"]


def test_delete_station(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    result = bridge.deleteStation("http://rock.stream")
    assert result["ok"]
    mock_radio_mgr.delete_station.assert_called_once_with(2)


def test_toggle_favorite(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.toggleFavorite(1)
    assert result["ok"]
    assert result["favorite"] is True
    mock_radio_mgr.favorite_station.assert_called_once_with(1)


def test_search_stations(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.search(query="Jazz")
    assert result["ok"]
    assert result["count"] >= 1


def test_search_empty_query(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.search(query="")
    assert result["ok"]


def test_edit_station(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.editStation(1, "Edited FM", "http://edited.stream", "MP3", "FR")
    assert result["ok"]
    mock_radio_mgr.edit_station.assert_called_once()
