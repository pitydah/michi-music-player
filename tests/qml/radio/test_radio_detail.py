from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import station_dicts, make_radio_service_mock


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

    def test_play_station_adds_to_history_on_confirmation(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        assert len(bridge.history) == 0
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 0  # not confirmed yet
        bridge._on_station_connection_done()
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
        result = bridge.retryCurrent()
        assert result["ok"]

    def test_reconnect_no_last(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"

    def test_cancel_stream_stops(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.cancelStream()
        assert result["ok"]

    def test_history_limited_to_fifty(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.get_history.side_effect = lambda limit=50: [
            {"name": f"S{i}", "url": f"http://s{i}", "played_at": "now"}
            for i in range(60)
        ][:limit]
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        assert len(bridge.history) <= 50

    def test_get_metadata_unavailable(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.getMetadata("http://jazz.stream")
        assert result["ok"] is False
        assert result["error"] == "NO_METADATA"

    def test_get_codec_default(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == ""

    def test_get_bitrate(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bitrate = bridge.getBitrate()
        assert bitrate == 0
