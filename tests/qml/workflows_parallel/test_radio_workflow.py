"""Workflow test: select station → play → reconnect → stop."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_stations():
    stations = []
    for i, (name, url, codec, country, fav) in enumerate([
        ("Jazz FM", "http://jazz.stream", "MP3", "US", True),
        ("Rock FM", "http://rock.stream", "AAC", "UK", False),
    ]):
        s = MagicMock()
        s.id = i + 1
        s.name = name
        s.url = url
        s.codec = codec
        s.country = country
        s.tags = [name.lower().split()[0]]
        s.favorite = fav
        s.bitrate = 128 + i * 64
        stations.append(s)
    return stations


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    mgr.get_metadata.return_value = {
        "ok": True, "title": "Song Title", "artist": "Artist Name"
    }
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


class TestRadioWorkflow:
    """Complete radio workflow: select → play → reconnect → stop."""

    def test_wf_list_stations(self, bridge):
        bridge.refresh()
        assert len(bridge.stations) == 2
        assert bridge.stations[0]["name"] == "Jazz FM"
        assert bridge.stations[1]["name"] == "Rock FM"

    def test_wf_select_and_play(self, bridge, mock_player):
        bridge.refresh()
        station = bridge.stations[1]
        result = bridge.playStation(station["url"])
        assert result["ok"]
        mock_player.play_url.assert_called_with(station["url"])

    def test_wf_play_updates_history(self, bridge):
        bridge.playStation("http://test.stream", "Test Station")
        assert len(bridge.history) >= 1
        assert bridge.history[0]["name"] == "Test Station"

    def test_wf_reconnect_last(self, bridge, mock_player):
        bridge.playStation("http://last.stream", "Last Station")
        bridge.stopStream()
        result = bridge.reconnectLast()
        assert result["ok"]
        mock_player.play_url.assert_called_with("http://last.stream")

    def test_wf_stop_while_playing(self, bridge, mock_player):
        bridge.playStation("http://playing.stream")
        result = bridge.stopStream()
        assert result["ok"]
        mock_player.stop.assert_called_once()

    def test_wf_select_favorite(self, bridge):
        bridge.refresh()
        assert len(bridge.favorites) == 1
        assert bridge.favorites[0]["name"] == "Jazz FM"

    def test_wf_toggle_favorite(self, bridge):
        bridge.refresh()
        bridge.toggleFavorite(2)
        assert bridge._favorites is not None

    def test_wf_play_without_selection(self, bridge, mock_player):
        result = bridge.playStation("http://direct.stream")
        assert result["ok"]
        mock_player.play_url.assert_called_once()

    def test_wf_stop_before_play(self, bridge, mock_player):
        result = bridge.stopStream()
        assert result["ok"]

    def test_wf_play_get_metadata(self, bridge, mock_radio_mgr):
        bridge.playStation("http://jazz.stream")
        metadata = bridge.getMetadata("http://jazz.stream")
        assert metadata["ok"]
        assert metadata["title"] == "Song Title"

    def test_wf_full_cycle(self, bridge, mock_player, mock_radio_mgr):
        bridge.refresh()
        assert len(bridge.stations) == 2
        station = bridge.stations[0]
        play_result = bridge.playStation(station["url"])
        assert play_result["ok"]
        mock_player.play_url.assert_called()
        reconnect_result = bridge.reconnectLast()
        assert reconnect_result["ok"]
        stop_result = bridge.stopStream()
        assert stop_result["ok"]
        mock_player.stop.assert_called()

    def test_wf_switch_stations(self, bridge, mock_player):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge.stopStream()
        bridge.playStation("http://rock.stream", "Rock FM")
        assert mock_player.play_url.call_count == 2
