<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test RadioBridge keyboard navigation patterns (bridge-level focus/activation)."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test keyboard navigation patterns for RadioPage and related components."""
=======
"""Test RadioBridge keyboard navigation patterns (bridge-level focus/activation)."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

<<<<<<< Updated upstream
<<<<<<< Updated upstream

@pytest.fixture
def mock_stations():
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("accessibility")]


@pytest.fixture
def mock_stations():
    stations = []
    for i, (name, url, codec, country, fav) in enumerate([
        ("Jazz FM", "http://jazz.stream", "MP3", "US", True),
        ("Rock FM", "http://rock.stream", "AAC", "UK", False),
        ("News Talk", "http://news.stream", "AAC", "US", True),
    ]):
        s = MagicMock()
        s.id = i + 1
        s.name = name
        s.url = url
        s.codec = codec
        s.country = country
        s.tags = [name.lower().split()[0]]
        s.favorite = fav
        s.bitrate = 128
        stations.append(s)
    return stations
=======

@pytest.fixture
def mock_stations():
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Station A"
    s1.url = "http://a.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["pop"]
    s1.favorite = False
    s1.bitrate = 128
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Station B"
    s2.url = "http://b.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock"]
    s2.favorite = False
    s2.bitrate = 256
    return [s1, s2]
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    mgr.remove_station.return_value = True
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    mgr.remove_station.return_value = True
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    return mgr


@pytest.fixture
def mock_player():
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    return MagicMock()
>>>>>>> Stashed changes


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
        assert mock_radio_mgr.toggle_favorite.called
        bridge.playStation("http://a.stream", "Station A")
        assert mock_player.play_url.called

    def test_edit_after_play(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
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
<<<<<<< Updated upstream
=======
        filtered = [r for r in result["results"] if r["name"] == "Jazz FM"]
        assert len(filtered) == 1
=======
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player


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
        assert mock_radio_mgr.toggle_favorite.called
        bridge.playStation("http://a.stream", "Station A")
        assert mock_player.play_url.called

    def test_edit_after_play(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

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
        assert len(bridge.history) == 3

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
        assert len(bridge.history) == 2

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
