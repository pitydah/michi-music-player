"""DS — Radio stream control v2: start/stop/reconnect/retry/timeout/cancel/metadata/buffer/errors."""
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
    player.stop.return_value = True
    return player


def test_start_stream(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("http://jazz.stream", "Jazz FM")
    assert result["ok"]
    assert result["accepted"] is True
    mock_radio_mgr.play_station.assert_called_once_with(
        "http://jazz.stream", "Jazz FM")


def test_stop_stream(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.stopStream()
    assert result["ok"]
    mock_radio_mgr.stop.assert_called_once()


def test_reconnect_last(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://jazz.stream", "Jazz FM")
    mock_radio_mgr.reset_mock()
    mock_radio_mgr.play_station.return_value = {"ok": True, "accepted": True, "status": "buffering"}
    result = bridge.reconnectLast()
    assert result["ok"]
    mock_radio_mgr.play_station.assert_called_once_with(
        "http://jazz.stream", "Jazz FM")


def test_retry_current(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://rock.stream", "Rock FM")
    mock_radio_mgr.reset_mock()
    mock_radio_mgr.play_station.return_value = {"ok": True, "accepted": True, "status": "buffering"}
    result = bridge.retryCurrent()
    assert result["ok"]
    mock_radio_mgr.play_station.assert_called_once_with(
        "http://rock.stream", "Rock FM")


def test_timeout_cancel(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://timeout.stream", "Timeout")
    result = bridge.cancelStream()
    assert result["ok"]
    mock_radio_mgr.stop.assert_called_once()


def test_stream_metadata_unavailable(mock_radio_mgr, mock_player):
    # The canonical service owns metadata; the bridge has no parallel client.
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.getMetadata("http://jazz.stream")
    assert not result["ok"]
    assert result["error"] == "NO_METADATA"


def test_buffer_state_default(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    assert bridge.getBitrate() == 0


def test_stream_error_on_play_failure(mock_radio_mgr, mock_player):
    mock_radio_mgr.play_station.return_value = {
        "ok": False, "error": "Connection refused"}
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.playStation("http://fail.stream")
    assert not result["ok"]
    assert "Connection refused" in result["error"]


def test_stream_error_on_stop_failure(mock_radio_mgr, mock_player):
    mock_radio_mgr.stop.side_effect = Exception("Stop error")
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
    assert bridge.stations[0]["codec"] == "MP3"
    assert bridge.getCodec() == ""


def test_reconnect_clears_error(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.playStation("http://jazz.stream", "Jazz FM")
    mock_radio_mgr.reset_mock()
    mock_radio_mgr.play_station.return_value = {"ok": True, "accepted": True, "status": "buffering"}
    result = bridge.reconnectLast()
    assert result["ok"]
