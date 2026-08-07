from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import make_radio_service_mock


@pytest.fixture
def mock_stations():
    return [
        {"id": 1, "name": "Jazz FM", "url": "http://jazz.stream", "codec": "MP3",
         "country": "US", "tags": [], "favorite": False, "image_path": "", "bitrate": 128},
        {"id": 2, "name": "Rock FM", "url": "http://rock.stream", "codec": "MP3",
         "country": "US", "tags": [], "favorite": False, "image_path": "", "bitrate": 128},
    ]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    return make_radio_service_mock(stations=mock_stations)


@pytest.fixture
def mock_player():
    return MagicMock()


class TestConnectionFailure:
    def test_play_station_player_fails(self, mock_radio_mgr):
        mock_radio_mgr.play_station.return_value = {
            "ok": False, "error": "Connection refused"}
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=MagicMock())
        result = bridge.playStation("http://fail.stream")
        assert not result["ok"]
        assert "error" in result

    def test_play_empty_url(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"

    def test_reconnect_no_last(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.reconnectLast()
        assert not result["ok"]
        assert result["error"] == "NO_LAST_STATION"


class TestInvalidUrl:
    def test_add_station_malformed_url(self, mock_radio_mgr, mock_player):
        # The bridge does not validate URLs; the canonical service does.
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("Bad", "not-a-url", "MP3", "")
        assert result["ok"]
        mock_radio_mgr.add_station.assert_called_once()

    def test_play_malformed_url(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("ftp://invalid")
        assert result["ok"]

    def test_add_station_empty_url(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("Test", "", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"


class TestUnavailableCodec:
    def test_get_codec_no_stations(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.get_stations.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == ""

    def test_get_codec_station_without_codec(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.get_stations.return_value = [
            {"id": 1, "name": "No Codec", "url": "http://stream.url", "codec": "",
             "country": "", "tags": [], "favorite": False, "image_path": "", "bitrate": 0},
        ]
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == ""


class TestNoManager:
    def test_no_radio_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.stations) == 0

    def test_no_manager_edit_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.editStation(1, "Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_no_manager_delete_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.deleteStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_no_manager_toggle_favorite_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.toggleFavorite(1)
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_no_manager_search_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.search(query="Jazz")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_no_manager_import_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.importM3u("/some/file.m3u")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"


class TestEdgeCases:
    def test_get_metadata_no_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.getMetadata("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_METADATA"

    def test_get_metadata_error(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.getMetadata("http://stream.url")
        assert not result["ok"]

    def test_export_opml_failure(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.exportOpml("/nonexistent/dir/stations.opml")
        assert not result["ok"]

    def test_export_m3u_without_stations(self, mock_radio_mgr, mock_player, tmp_path):
        mock_radio_mgr.get_stations.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "empty.m3u"
        result = bridge.exportM3u(str(out))
        assert not result["ok"]
        assert result["error"] == "NO_STATIONS"
