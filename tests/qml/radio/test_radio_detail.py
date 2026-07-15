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
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    return player


class TestRadioDetail:

    def test_station_count(self, mock_radio_mgr, mock_player):
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

        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"

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

    def test_get_bitrate(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bitrate = bridge.getBitrate()
        assert bitrate == 0
