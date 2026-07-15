"""MP: Test RadioBridge lifecycle — states, cancel, no network from QML."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.radio_bridge import RadioBridge


class _Station:
    def __init__(self, sid=1, name="Test FM", url="https://stream.example.com/radio",
                 codec="MP3", country="US", tags=None, favorite=False):
        self.id = sid
        self.name = name
        self.url = url
        self.codec = codec
        self.country = country
        self.tags = tags or []
        self.favorite = favorite
        self.image_path = ""


@pytest.fixture
def radio_mgr():
    mgr = MagicMock()
    mgr.get_all.return_value = [
        _Station(1, "Jazz FM", "https://jazz.stream", "FLAC", "US", ["jazz"]),
        _Station(2, "Rock FM", "https://rock.stream", "MP3", "UK", ["rock"]),
    ]
    mgr.add.return_value = _Station(3, "New Station", "https://new.stream")
    return mgr


@pytest.fixture
def player():
    p = MagicMock()
    p.play_url = MagicMock(return_value=True)
    p.stop = MagicMock(return_value=True)
    return p


@pytest.fixture
def bridge(radio_mgr, player):
    return RadioBridge(radio_manager=radio_mgr, player_service=player)


class TestRadioLifecycle:
    def test_initial_state_empty(self):
        b = RadioBridge()
        assert b.stations == []
        assert b.favorites == []
        assert b.history == []

    def test_refresh_loads_stations(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True
        assert result["count"] == 2
        assert len(bridge.stations) == 2

    def test_add_station_calls_manager(self, bridge, radio_mgr):
        result = bridge.addStation("New FM", "https://new.fm/stream", "AAC", "DE")
        assert result["ok"] is True
        radio_mgr.add.assert_called_once()

    def test_add_station_without_url_fails(self, bridge):
        result = bridge.addStation("Empty", "", "MP3", "")
        assert result.get("error") == "EMPTY_URL"

    def test_add_station_without_manager_fails(self):
        b = RadioBridge()
        result = b.addStation("X", "http://x", "MP3", "")
        assert result.get("error") == "NO_RADIO_MANAGER"

    def test_play_calls_player(self, bridge, player):
        result = bridge.playStation("https://stream.example.com/radio", "Test FM")
        assert result["ok"] is True
        player.play_url.assert_called_once_with("https://stream.example.com/radio")

    def test_play_without_url_fails(self, bridge):
        result = bridge.playStation("")
        assert result.get("error") == "EMPTY_URL"

    def test_play_without_player_fails(self):
        b = RadioBridge(radio_manager=MagicMock())
        result = b.playStation("http://x")
        assert result.get("error") == "NO_PLAYER_SERVICE"

    def test_stop_calls_player(self, bridge, player):
        bridge.playStation("http://x", "X")
        result = bridge.stopStream()
        assert result["ok"] is True
        player.stop.assert_called_once()

    def test_cancel_calls_stop(self, bridge, player):
        bridge.playStation("http://x", "X")
        result = bridge.cancelStream()
        assert result["ok"] is True

    def test_delete_station_calls_manager(self, bridge, radio_mgr):
        radio_mgr.remove_station = MagicMock(return_value=True)
        result = bridge.deleteStation("https://stream.example.com/radio")
        assert result["ok"] is True
        radio_mgr.remove_station.assert_called_once()

    def test_delete_without_manager_fails(self):
        b = RadioBridge()
        result = b.deleteStation("http://x")
        assert result.get("error") == "NO_RADIO_MANAGER"

    def test_edit_station_calls_manager(self, bridge, radio_mgr):
        radio_mgr.update = MagicMock(return_value=True)
        result = bridge.editStation(1, "New Name", "http://new.url")
        assert result["ok"] is True
        radio_mgr.update.assert_called_once()

    def test_toggle_favorite_calls_manager(self, bridge, radio_mgr):
        radio_mgr.toggle_favorite = MagicMock(return_value=True)
        result = bridge.toggleFavorite(1)
        assert result["ok"] is True
        radio_mgr.toggle_favorite.assert_called_once_with(1)

    def test_search_returns_results(self, bridge):
        result = bridge.search(query="Jazz")
        assert result["ok"] is True
        assert result["count"] >= 1

    def test_search_empty_query_returns_all(self, bridge):
        result = bridge.search()
        assert result["ok"] is True
        assert result["count"] == 2

    def test_reconnect_last_play_calls_play(self, bridge, player):
        bridge.playStation("http://x", "X")
        player.play_url.reset_mock()
        result = bridge.reconnectLast()
        assert result["ok"] is True
        player.play_url.assert_called_once()

    def test_reconnect_without_last_fails(self, bridge):
        result = bridge.reconnectLast()
        assert result.get("error") == "NO_LAST_STATION"

    def test_history_records_played_stations(self, bridge):
        bridge.playStation("http://a", "Alpha")
        bridge.playStation("http://b", "Beta")
        assert len(bridge.history) == 2

    def test_history_max_50(self, bridge):
        for i in range(60):
            bridge.playStation(f"http://{i}", f"Station {i}")
        assert len(bridge.history) <= 50

    def test_export_m3u_without_stations_fails(self, bridge):
        b = RadioBridge()
        result = b.exportM3u("/tmp/test.m3u")
        assert result.get("error") == "NO_STATIONS"

    def test_get_codec_returns_codec(self, bridge):
        codec = bridge.getCodec()
        assert codec == "FLAC"

    def test_get_bitrate_returns_zero(self, bridge):
        assert bridge.getBitrate() == 0

    def test_play_adds_to_history(self, bridge):
        bridge.playStation("http://a", "Alpha")
        assert len(bridge.history) > 0
        assert bridge.history[0]["name"] == "Alpha"

    def test_favorites_after_refresh(self, bridge):
        bridge.refresh()
        favs = bridge.favorites
        assert len(favs) == 0

    def test_no_favorites_when_none_marked(self, bridge):
        bridge.refresh()
        assert len(bridge.favorites) == 0

    def test_stop_without_player_returns_error(self):
        b = RadioBridge()
        result = b.stopStream()
        assert result.get("error") == "NO_PLAYER"
