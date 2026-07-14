"""Test radio station workflows through RadioBridge."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge


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
    return mgr


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
    mock_radio_mgr.add.assert_called_once()


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
    mock_radio_mgr.remove_station.return_value = True
    result = bridge.deleteStation("http://rock.stream")
    assert result["ok"]
    mock_radio_mgr.remove_station.assert_called_once()


def test_toggle_favorite(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.toggleFavorite(1)
    assert result["ok"]
    assert result["favorite"] is True
    mock_radio_mgr.toggle_favorite.assert_called_once_with(1)


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
    mock_radio_mgr.update.return_value = True
    result = bridge.editStation(1, "Edited FM", "http://edited.stream", "MP3", "FR")
    assert result["ok"]
    mock_radio_mgr.update.assert_called_once()
