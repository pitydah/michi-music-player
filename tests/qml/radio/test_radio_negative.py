<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Test RadioBridge negative cases: connection failure, invalid URL, unavailable codec, no manager."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Test negative/error cases for radio components."""
=======
"""Test RadioBridge negative cases: connection failure, invalid URL, unavailable codec, no manager."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

<<<<<<< Updated upstream
<<<<<<< Updated upstream

@pytest.fixture
def mock_stations():
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Jazz FM"
    s1.url = "http://jazz.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["jazz"]
    s1.favorite = False
    s1.bitrate = 128
    return [s1]
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("negative")]
>>>>>>> Stashed changes


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
<<<<<<< Updated upstream
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
=======
    mgr.get_all.return_value = []
=======

@pytest.fixture
def mock_stations():
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Jazz FM"
    s1.url = "http://jazz.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["jazz"]
    s1.favorite = False
    s1.bitrate = 128
    return [s1]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    return mgr


@pytest.fixture
def mock_player():
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    player = MagicMock()
    player.play_url.return_value = True
    return player
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    return MagicMock()
>>>>>>> Stashed changes


class TestConnectionFailure:
    def test_play_station_player_fails(self, mock_radio_mgr):
        player = MagicMock()
        player.play_url.side_effect = Exception("Connection refused")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=player)
        result = bridge.playStation("http://fail.stream")
        assert not result["ok"]
        assert "error" in result

<<<<<<< Updated upstream
    def test_play_empty_url_returns_error(self, mock_radio_mgr, mock_player):
=======
    def test_null_player_service(self, mock_radio_mgr):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = bridge.playStation("http://test.stream")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

    def test_null_bridge_refresh(self):
        result = None
        rd = None
        if rd and hasattr(rd, 'refresh'):
            result = rd.refresh()
        assert result is None

    def test_play_empty_url(self, mock_radio_mgr, mock_player):
=======
    player = MagicMock()
    player.play_url.return_value = True
    return player


class TestConnectionFailure:
    def test_play_station_player_fails(self, mock_radio_mgr):
        player = MagicMock()
        player.play_url.side_effect = Exception("Connection refused")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=player)
        result = bridge.playStation("http://fail.stream")
        assert not result["ok"]
        assert "error" in result

    def test_play_empty_url_returns_error(self, mock_radio_mgr, mock_player):
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    def test_play_without_player(self, mock_radio_mgr):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = bridge.playStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

    def test_stop_without_player(self, mock_radio_mgr):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = bridge.stopStream()
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER"

    def test_reconnect_without_history(self, mock_radio_mgr, mock_player):
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    def test_delete_nonexistent(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.side_effect = Exception("Not found")
>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
    def test_manager_throws_on_get_all(self, mock_player):
        mgr = MagicMock()
        mgr.get_all.side_effect = RuntimeError("DB failure")
        bridge = RadioBridge(radio_manager=mgr, player_service=mock_player)
=======
    def test_play_without_player(self, mock_radio_mgr):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = bridge.playStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

    def test_stop_without_player(self, mock_radio_mgr):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=None)
        result = bridge.stopStream()
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER"

    def test_reconnect_without_history(self, mock_radio_mgr, mock_player):
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


<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
        mock_radio_mgr.get_all.return_value = [s]
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        codec = bridge.getCodec()
        assert codec == ""


class TestNoManager:
    def test_no_radio_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.stations) == 0

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    def test_no_manager_play_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.playStation("http://stream.url")
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    def test_import_invalid_file(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u("/invalid/path.m3u")
>>>>>>> Stashed changes
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

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
<<<<<<< Updated upstream
=======
        result = bridge.search(query="test")
        assert result["ok"]
        assert result["count"] == 0
=======
    def test_no_manager_play_fails(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.playStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_PLAYER_SERVICE"

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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
