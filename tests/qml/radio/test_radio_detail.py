<<<<<<< Updated upstream
"""Test RadioBridge station detail operations."""
=======
<<<<<<< HEAD
"""Test RadioStationDetailPage states and metadata display."""
=======
"""Test RadioBridge station detail operations."""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("detail")]

=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    s1.language = "English"
    s1.genre = "Jazz"
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Rock FM"
    s2.url = "http://rock.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock", "classic"]
    s2.favorite = False
    s2.bitrate = 256
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    s2.language = "English"
    s2.genre = "Rock"
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return [s1, s2]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
<<<<<<< Updated upstream
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
=======
<<<<<<< HEAD
    mgr.get_metadata.return_value = {"ok": True, "title": "Now Playing", "artist": "Artist"}
=======
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    return player


<<<<<<< Updated upstream
class TestStationDetail:
    def test_station_data_available(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
=======
<<<<<<< HEAD
@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestRadioDetail:
    """Test station detail display and metadata."""

    def test_station_data_structure(self, bridge):
>>>>>>> Stashed changes
        bridge.refresh()
        assert len(bridge.stations) == 2
        assert bridge.stations[0]["name"] == "Jazz FM"
        assert bridge.stations[0]["codec"] == "MP3"
        assert bridge.stations[0]["country"] == "US"
        assert bridge.stations[0]["url"] == "http://jazz.stream"

    def test_station_has_tags(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert "jazz" in bridge.stations[0]["tags"]

    def test_play_station_returns_ok(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"]
        assert mock_player.play_url.called

    def test_play_station_adds_to_history(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.history) == 0
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Jazz FM"
        assert bridge.history[0]["url"] == "http://jazz.stream"

    def test_stop_stream(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.stopStream()
        assert result["ok"]
        assert mock_player.stop.called

    def test_reconnect_last(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.reconnectLast()
        assert result["ok"]

<<<<<<< Updated upstream
    def test_reconnect_without_history_returns_error(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
=======
    def test_reconnect_without_last(self, bridge):
=======
class TestStationDetail:
    def test_station_data_available(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.stations) == 2
        assert bridge.stations[0]["name"] == "Jazz FM"
        assert bridge.stations[0]["codec"] == "MP3"
        assert bridge.stations[0]["country"] == "US"
        assert bridge.stations[0]["url"] == "http://jazz.stream"

    def test_station_has_tags(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert "jazz" in bridge.stations[0]["tags"]

    def test_play_station_returns_ok(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"]
        assert mock_player.play_url.called

    def test_play_station_adds_to_history(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.history) == 0
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Jazz FM"
        assert bridge.history[0]["url"] == "http://jazz.stream"

    def test_stop_stream(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.stopStream()
        assert result["ok"]
        assert mock_player.stop.called

    def test_reconnect_last(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.reconnectLast()
        assert result["ok"]

    def test_reconnect_without_history_returns_error(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"

<<<<<<< Updated upstream
    def test_retry_current(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
=======
<<<<<<< HEAD
    def test_retry_current(self, bridge, mock_player):
        bridge.playStation("http://retry.stream")
>>>>>>> Stashed changes
        result = bridge.retryCurrent()
        assert result["ok"]

    def test_cancel_stream_stops(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.cancelStream()
        assert result["ok"]

    def test_history_limited_to_fifty(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        for i in range(60):
            bridge.playStation(f"http://stream{i}.url", f"Station {i}")
        assert len(bridge.history) <= 50

    def test_get_metadata_called(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.get_metadata.return_value = {"ok": True, "title": "Song", "artist": "Artist"}
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.getMetadata("http://jazz.stream")
        assert result["ok"]
        assert result["title"] == "Song"

    def test_get_codec_from_stations(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == "MP3"

<<<<<<< Updated upstream
=======
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
=======
    def test_retry_current(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.retryCurrent()
        assert result["ok"]

    def test_cancel_stream_stops(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.cancelStream()
        assert result["ok"]

    def test_history_limited_to_fifty(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        for i in range(60):
            bridge.playStation(f"http://stream{i}.url", f"Station {i}")
        assert len(bridge.history) <= 50

    def test_get_metadata_called(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.get_metadata.return_value = {"ok": True, "title": "Song", "artist": "Artist"}
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.getMetadata("http://jazz.stream")
        assert result["ok"]
        assert result["title"] == "Song"

    def test_get_codec_from_stations(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == "MP3"

>>>>>>> Stashed changes
    def test_get_bitrate(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bitrate = bridge.getBitrate()
        assert bitrate == 0
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
