"""MP: Test RadioBridge lifecycle — states, cancel, no network from QML."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import make_radio_service_mock


def _lifecycle_stations():
    return [
        {"id": 1, "name": "Jazz FM", "url": "https://jazz.stream", "codec": "FLAC",
         "country": "US", "tags": ["jazz"], "favorite": False, "image_path": "", "bitrate": 0},
        {"id": 2, "name": "Rock FM", "url": "https://rock.stream", "codec": "MP3",
         "country": "UK", "tags": ["rock"], "favorite": False, "image_path": "", "bitrate": 0},
    ]


@pytest.fixture
def radio_mgr():
    return make_radio_service_mock(stations=_lifecycle_stations())


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
        radio_mgr.add_station.assert_called_once()

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
        bridge.refresh()
        result = bridge.deleteStation("https://rock.stream")
        assert result["ok"] is True
        radio_mgr.delete_station.assert_called_once()

    def test_delete_without_manager_fails(self):
        b = RadioBridge()
        result = b.deleteStation("http://x")
        assert result.get("error") == "NO_RADIO_MANAGER"

    def test_edit_station_calls_manager(self, bridge, radio_mgr):
        result = bridge.editStation(1, "New Name", "http://new.url")
        assert result["ok"] is True
        radio_mgr.edit_station.assert_called_once()

    def test_toggle_favorite_calls_manager(self, bridge, radio_mgr):
        result = bridge.toggleFavorite(1)
        assert result["ok"] is True
        radio_mgr.favorite_station.assert_called_once_with(1)

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
        bridge.playStation("https://jazz.stream", "Jazz FM")
        bridge.playStation("https://rock.stream", "Rock FM")
        assert len(bridge.history) == 0
        bridge._on_station_connection_done()
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Rock FM"

    def test_history_max_50(self, bridge):
        radio_mgr = bridge.radio_manager
        radio_mgr.get_history.side_effect = lambda limit=50: [
            {"name": f"Station {i}", "url": f"http://{i}", "played_at": "now"}
            for i in range(60)
        ][:limit]
        assert len(bridge.history) <= 50

    def test_export_m3u_without_stations_fails(self, bridge):
        b = RadioBridge()
        result = b.exportM3u("/tmp/test.m3u")
        assert result.get("error") == "NO_STATIONS"

    def test_get_codec_from_station(self, bridge):
        bridge.refresh()
        assert bridge.stations[0]["codec"] == "FLAC"
        assert bridge.getCodec() == ""

    def test_get_bitrate_returns_zero(self, bridge):
        assert bridge.getBitrate() == 0

    def test_play_adds_to_history_on_confirmation(self, bridge):
        bridge.playStation("https://jazz.stream", "Jazz FM")
        assert len(bridge.history) == 0
        bridge._on_station_connection_done()
        assert len(bridge.history) == 1
        assert bridge.history[0]["name"] == "Jazz FM"

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
