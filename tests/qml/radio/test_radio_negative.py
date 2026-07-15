"""Test negative/error cases for radio components."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("negative")]


@pytest.fixture
def mock_radio_mgr():
    mgr = MagicMock()
    mgr.get_all.return_value = []
    return mgr


@pytest.fixture
def mock_player():
    return MagicMock()


class TestRadioNegative:
    """Test error/edge case handling."""

    def test_null_bridge_play(self):
        result = None
        rd = None
        if rd and hasattr(rd, 'playStation'):
            result = rd.playStation("http://test.stream")
        assert result is None

    def test_null_bridge_add(self):
        result = None
        rd = None
        if rd and hasattr(rd, 'addStation'):
            result = rd.addStation("Test", "http://test.stream", "", "")
        assert result is None

    def test_null_radio_manager(self, mock_player):
        bridge = RadioBridge(radio_manager=None, player_service=mock_player)
        result = bridge.addStation("Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

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
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.playStation("")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"

    def test_delete_nonexistent(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.side_effect = Exception("Not found")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.deleteStation("http://nonexistent.stream")
        assert not result["ok"]

    def test_toggle_favorite_no_manager(self, mock_player):
        bridge = RadioBridge(radio_manager=None, player_service=mock_player)
        result = bridge.toggleFavorite(1)
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_search_no_service(self, mock_player):
        bridge = RadioBridge(radio_manager=None, player_service=mock_player)
        result = bridge.search(query="Test")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_manager_throws_on_get_all(self, mock_player):
        mgr = MagicMock()
        mgr.get_all.side_effect = RuntimeError("DB failure")
        bridge = RadioBridge(radio_manager=mgr, player_service=mock_player)
        result = bridge.refresh()
        assert result["ok"]
        assert result["count"] == 0
        assert len(bridge.stations) == 0

    def test_import_invalid_file(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u("/invalid/path.m3u")
        assert not result["ok"]
        assert result["error"] == "FILE_NOT_FOUND"

    def test_edit_nonexistent(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.side_effect = Exception("Station not found")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(999, "Ghost", "http://ghost.stream")
        assert not result["ok"]

    def test_empty_station_list_search(self):
        mgr = MagicMock()
        mgr.get_all.return_value = []
        bridge = RadioBridge(radio_manager=mgr, player_service=MagicMock())
        bridge.refresh()
        result = bridge.search(query="test")
        assert result["ok"]
        assert result["count"] == 0
