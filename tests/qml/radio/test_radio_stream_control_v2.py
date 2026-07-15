"""DS — Radio stream control v2: start/stop/reconnect/retry/timeout/cancel/metadata/buffer/errors."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
pytestmark = [pytest.mark.qml_module("radio")]



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
    mgr.get_metadata.return_value = {"ok": True, "title": "Song", "artist": "Artist"}
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    player.stop.return_value = True
    return player


def test_start_stream(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("http://jazz.stream", "Jazz FM")
    assert result["ok"]
    mock_player.play_url.assert_called_once_with("http://jazz.stream")


def test_stop_stream(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.stopStream()
    assert result["ok"]
    mock_player.stop.assert_called_once()


def test_reconnect_last(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://jazz.stream", "Jazz FM")
    mock_player.reset_mock()
    result = bridge.reconnectLast()
    assert result["ok"]
    mock_player.play_url.assert_called_once_with("http://jazz.stream")


def test_retry_current(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://rock.stream", "Rock FM")
    mock_player.reset_mock()
    result = bridge.retryCurrent()
    assert result["ok"]
    mock_player.play_url.assert_called_once_with("http://rock.stream")


def test_timeout_cancel(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://timeout.stream", "Timeout")
    result = bridge.cancelStream()
    assert result["ok"]
    mock_player.stop.assert_called_once()


def test_stream_metadata(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.getMetadata("http://jazz.stream")
    assert result["ok"]
    assert result["title"] == "Song"


def test_buffer_state_default(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    assert bridge.getBitrate() == 0


def test_stream_error_on_play_failure(mock_radio_mgr, mock_player):
    mock_player.play_url.side_effect = Exception("Connection refused")
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("http://fail.stream")
    assert not result["ok"]
    assert "Connection refused" in result["error"]


def test_stream_error_on_stop_failure(mock_radio_mgr, mock_player):
    mock_player.stop.side_effect = Exception("Stop error")
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.stopStream()
    assert not result["ok"]


def test_reconnect_no_last(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.reconnectLast()
    assert not result["ok"]
    assert result["error"] == "NO_LAST_STATION"


def test_codec_string(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    codec = bridge.getCodec()
    assert codec == "MP3"


def test_reconnect_clears_error(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://jazz.stream", "Jazz FM")
    mock_player.reset_mock()
    result = bridge.reconnectLast()
    assert result["ok"]
