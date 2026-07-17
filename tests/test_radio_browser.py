from unittest.mock import MagicMock, patch

from ui_qml_bridge.radio_bridge import RadioBridge


class TestRadioBrowserApi:
    def test_radio_bridge_initializes(self):
        bridge = RadioBridge(player_service=MagicMock())
        assert bridge is not None
        assert bridge._player is not None
        assert bridge._stations == []
        assert bridge._favorites == []

    @patch("ui_qml_bridge.radio_bridge.logger")
    def test_radio_bridge_search(self, mock_logger):
        mock_mgr = MagicMock()
        mock_station = MagicMock()
        mock_station.id = 1
        mock_station.name = "Test FM"
        mock_station.url = "http://test.stream/audio"
        mock_station.codec = "MP3"
        mock_station.country = "Testland"
        mock_station.tags = ["pop", "rock"]
        mock_station.favorite = False
        mock_station.bitrate = 128
        mock_station.image_path = ""
        mock_mgr.get_all.return_value = [mock_station]

        bridge = RadioBridge(radio_manager=mock_mgr, player_service=MagicMock())
        result = bridge.search(query="Test")

        assert result["ok"] is True
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Test FM"
        assert result["results"][0]["url"] == "http://test.stream/audio"

    @patch("ui_qml_bridge.radio_bridge.logger")
    def test_radio_bridge_search_empty(self, mock_logger):
        mock_mgr = MagicMock()
        mock_mgr.get_all.return_value = []

        bridge = RadioBridge(radio_manager=mock_mgr, player_service=MagicMock())
        result = bridge.search(query="Nothing")

        assert result["ok"] is True
        assert result["count"] == 0
        assert result["results"] == []

    @patch("ui_qml_bridge.radio_bridge.logger")
    def test_radio_bridge_search_error(self, mock_logger):
        mock_mgr = MagicMock()
        mock_mgr.get_all.side_effect = ConnectionError("Network failure")

        bridge = RadioBridge(radio_manager=mock_mgr, player_service=MagicMock())
        result = bridge.search(query="Test")

        assert result["ok"] is False
        assert "Network failure" in result["error"]

    def test_radio_station_detail(self):
        station = {
            "id": 42,
            "name": "Jazz FM",
            "url": "http://jazz.stream/128",
            "codec": "FLAC",
            "country": "France",
            "tags": ["jazz", "fusion"],
            "favorite": True,
            "bitrate": 320,
            "image_path": "/tmp/icon.png",
        }
        assert station["id"] == 42
        assert station["name"] == "Jazz FM"
        assert station["url"] == "http://jazz.stream/128"
        assert station["codec"] == "FLAC"
        assert station["country"] == "France"
        assert station["tags"] == ["jazz", "fusion"]
        assert station["favorite"] is True
        assert station["bitrate"] == 320
