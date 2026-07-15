from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge


@pytest.fixture
def mock_stations():
    stations = []
    for i, (name, url) in enumerate([
        ("Jazz FM", "http://jazz.stream"),
        ("Rock FM", "http://rock.stream"),
    ]):
        s = MagicMock()
        s.id = i + 1
        s.name = name
        s.url = url
        s.codec = "MP3"
        s.country = "US"
        s.tags = []
        s.favorite = False
        s.bitrate = 128
        s.image_path = ""
        stations.append(s)
    return stations


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    return mgr


@pytest.fixture
def mock_player():
    return MagicMock()


class TestConnectionFailure:
    def test_play_station_player_fails(self, mock_radio_mgr):
        player = MagicMock()
        player.play_url.side_effect = Exception("Connection refused")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=player)
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
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("Bad", "not-a-url", "MP3", "")
        assert result["ok"]

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
        mock_radio_mgr.get_all.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == ""

    def test_get_codec_station_without_codec(self, mock_radio_mgr, mock_player):
        s = MagicMock()
        s.codec = ""
        s.name = "No Codec"
        s.url = "http://stream.url"
        s.country = ""
        s.tags = []
        s.favorite = False
        s.bitrate = 0
        s.image_path = ""
        mock_radio_mgr.get_all.return_value = [s]
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
        mock_radio_mgr.get_metadata.side_effect = Exception("Metadata error")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.getMetadata("http://stream.url")
        assert not result["ok"]

    def test_export_opml_failure(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.exportOpml("/nonexistent/dir/stations.opml")
        assert not result["ok"]

    def test_export_m3u_without_stations(self, mock_radio_mgr, mock_player, tmp_path):
        mock_radio_mgr.get_all.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "empty.m3u"
        result = bridge.exportM3u(str(out))
        assert not result["ok"]
        assert result["error"] == "NO_STATIONS"
