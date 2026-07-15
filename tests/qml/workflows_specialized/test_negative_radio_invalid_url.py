"""MX: Negative — invalid radio URL scenarios."""
from __future__ import annotations

from ui_qml_bridge.radio_bridge import RadioBridge


def test_empty_url():
    bridge = RadioBridge()
    result = bridge.playStation("")
    assert result.get("ok") is False
    assert result.get("error") == "EMPTY_URL"


def test_null_url():
    bridge = RadioBridge()
    result = bridge.playStation(None)
    assert result.get("ok") is False


def test_malformed_url():
    bridge = RadioBridge()
    result = bridge.playStation("not-a-valid-url")
    assert result.get("ok") is False


def test_no_player_service():
    bridge = RadioBridge(radio_manager=None)
    result = bridge.playStation("http://stream.example.com/radio")
    assert result.get("ok") is False


def test_add_station_empty_name():
    bridge = RadioBridge()
    result = bridge.addStation("", "http://stream.url", "MP3", "US")
    assert result.get("ok") is False or result.get("error") is not None


def test_add_station_invalid_url():
    bridge = RadioBridge()
    result = bridge.addStation("Test", "not-a-url", "MP3", "US")
    assert result.get("ok") is False or result.get("error") is not None


def test_delete_nonexistent_station():
    bridge = RadioBridge()
    result = bridge.deleteStation("http://nonexistent.stream/radio")
    assert result.get("ok") is True or result.get("error") == "NO_RADIO_MANAGER"
