<<<<<<< Updated upstream
"""Test RadioBridge add/edit station operations."""
=======
<<<<<<< HEAD
"""Test RadioEditorDialog and RadioImportDialog logic for station management."""
=======
"""Test RadioBridge add/edit station operations."""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

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
    s1.favorite = True
    return [s1]
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("editor")]
>>>>>>> Stashed changes


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
<<<<<<< Updated upstream
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
=======
    mgr.add.return_value = MagicMock(id=99)
    mgr.update.return_value = True
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
    s1.favorite = True
    return [s1]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return mgr


@pytest.fixture
def mock_player():
<<<<<<< Updated upstream
    player = MagicMock()
    player.play_url.return_value = True
    return player
=======
<<<<<<< HEAD
    return MagicMock()
>>>>>>> Stashed changes


class TestAddStation:
    def test_add_station_success(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("New FM", "http://new.stream", "AAC", "FR")
        assert result["ok"]
        mock_radio_mgr.add.assert_called_once()

<<<<<<< Updated upstream
    def test_add_station_empty_url_returns_error(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
=======
    def test_add_station_empty_url(self, bridge):
=======
    player = MagicMock()
    player.play_url.return_value = True
    return player


class TestAddStation:
    def test_add_station_success(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("New FM", "http://new.stream", "AAC", "FR")
        assert result["ok"]
        mock_radio_mgr.add.assert_called_once()

    def test_add_station_empty_url_returns_error(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.addStation("Test", "", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"

<<<<<<< Updated upstream
    def test_add_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.addStation("Test", "http://test.stream", "MP3", "")
=======
<<<<<<< HEAD
    def test_add_station_no_manager(self):
        b = RadioBridge(radio_manager=None, player_service=MagicMock())
        result = b.addStation("Test", "http://test.stream", "MP3", "")
>>>>>>> Stashed changes
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_add_station_returns_id(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("Jazz FM", "http://jazz.stream", "MP3", "US")
        assert result["ok"]
        assert result["id"] == 1

    def test_add_station_with_country(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("DE Station", "http://de.stream", "MP3", "DE")
        assert result["ok"]

    def test_add_station_triggers_refresh(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.addStation("New", "http://new.stream", "MP3", "US")
        assert len(bridge.stations) > 0

    def test_add_station_empty_name_ok(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("", "http://stream.url", "MP3", "")
        assert result["ok"]


class TestEditStation:
    def test_edit_station_success(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Edited FM", "http://edited.stream", "AAC", "FR")
        assert result["ok"]
        mock_radio_mgr.update.assert_called_once_with(1, name="Edited FM", url="http://edited.stream")

    def test_edit_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.editStation(1, "Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_edit_station_triggers_refresh(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.editStation(1, "Edited", "http://edited.stream", "AAC", "UK")
        assert len(bridge.stations) > 0

    def test_edit_station_no_update_method(self, mock_radio_mgr, mock_player):
        del mock_radio_mgr.update
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NOT_IMPLEMENTED"

    def test_edit_station_failure(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.side_effect = Exception("Update failed")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Fail", "http://fail.stream", "MP3", "")
        assert not result["ok"]

    def test_edit_all_fields(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Full Edit", "http://full.stream", "OGG", "BR")
        assert result["ok"]
        mock_radio_mgr.update.assert_called_once_with(1, name="Full Edit", url="http://full.stream")


class TestDeleteStation:
    def test_delete_station_success(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.deleteStation("http://jazz.stream")
        assert result["ok"]
        mock_radio_mgr.remove_station.assert_called_once()

    def test_delete_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.deleteStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_delete_nonexistent(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.deleteStation("http://nonexistent.stream")
        assert result["ok"]


class TestToggleFavorite:
    def test_toggle_favorite_on(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.toggle_favorite.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.toggleFavorite(1)
        assert result["ok"]
<<<<<<< Updated upstream
=======
        call_args = mock_radio_mgr.add.call_args
        assert call_args[0][0] == "Deutschlandfunk"
        assert call_args[1] == "http://dradio.stream"
=======
    def test_add_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.addStation("Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_add_station_returns_id(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("Jazz FM", "http://jazz.stream", "MP3", "US")
        assert result["ok"]
        assert result["id"] == 1

    def test_add_station_with_country(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("DE Station", "http://de.stream", "MP3", "DE")
        assert result["ok"]

    def test_add_station_triggers_refresh(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.addStation("New", "http://new.stream", "MP3", "US")
        assert len(bridge.stations) > 0

    def test_add_station_empty_name_ok(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.addStation("", "http://stream.url", "MP3", "")
        assert result["ok"]


class TestEditStation:
    def test_edit_station_success(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Edited FM", "http://edited.stream", "AAC", "FR")
        assert result["ok"]
        mock_radio_mgr.update.assert_called_once_with(1, name="Edited FM", url="http://edited.stream")

    def test_edit_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.editStation(1, "Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_edit_station_triggers_refresh(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.editStation(1, "Edited", "http://edited.stream", "AAC", "UK")
        assert len(bridge.stations) > 0

    def test_edit_station_no_update_method(self, mock_radio_mgr, mock_player):
        del mock_radio_mgr.update
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NOT_IMPLEMENTED"

    def test_edit_station_failure(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.side_effect = Exception("Update failed")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Fail", "http://fail.stream", "MP3", "")
        assert not result["ok"]

    def test_edit_all_fields(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.update.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.editStation(1, "Full Edit", "http://full.stream", "OGG", "BR")
        assert result["ok"]
        mock_radio_mgr.update.assert_called_once_with(1, name="Full Edit", url="http://full.stream")


class TestDeleteStation:
    def test_delete_station_success(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.deleteStation("http://jazz.stream")
        assert result["ok"]
        mock_radio_mgr.remove_station.assert_called_once()

    def test_delete_station_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.deleteStation("http://stream.url")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_delete_nonexistent(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.remove_station.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.deleteStation("http://nonexistent.stream")
        assert result["ok"]


class TestToggleFavorite:
    def test_toggle_favorite_on(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.toggle_favorite.return_value = True
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.toggleFavorite(1)
        assert result["ok"]
>>>>>>> Stashed changes
        assert result["favorite"] is True

    def test_toggle_favorite_off(self, mock_radio_mgr, mock_player):
        mock_radio_mgr.toggle_favorite.return_value = False
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.toggleFavorite(1)
        assert result["ok"]
        assert result["favorite"] is False

    def test_toggle_favorite_without_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.toggleFavorite(1)
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_toggle_favorite_without_method(self, mock_radio_mgr, mock_player):
        del mock_radio_mgr.toggle_favorite
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.toggleFavorite(1)
        assert not result["ok"]
        assert result["error"] == "NOT_IMPLEMENTED"
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
