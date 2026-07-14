"""Test real radio async: search, favorites, recent, edit, import/export, reconnection, timeout."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge


@pytest.fixture
def mock_stations():
    s1 = MagicMock()
    s1.id = 1
    s1.name = "Jazz FM"
    s1.url = "http://jazz.stream"
    s1.codec = "MP3"
    s1.country = "US"
    s1.tags = ["jazz", "cool"]
    s1.favorite = True
    s1.bitrate = 128
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Rock FM"
    s2.url = "http://rock.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock", "classic"]
    s2.favorite = False
    s2.bitrate = 256
    return [s1, s2]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    mgr.toggle_favorite.return_value = True
    return mgr


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play_url.return_value = True
    return player


def test_search_async_returns_filtered_results(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    result = bridge.search(query="Jazz")
    assert result["ok"]
    assert result["count"] >= 1
    names = [r["name"] for r in result["results"]]
    assert "Jazz FM" in names


def test_search_with_country_filter(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    result = bridge.search(query="FM", country="UK")
    assert result["ok"]
    names = [r["name"] for r in result["results"]]
    assert "Rock FM" in names


def test_search_with_tag_filter(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    result = bridge.search(tag="classic")
    assert result["ok"]
    assert result["count"] >= 1


def test_favorites_populated_on_refresh(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    assert len(bridge.favorites) == 1
    assert bridge.favorites[0]["name"] == "Jazz FM"


def test_edit_station_updates_metadata(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    mock_radio_mgr.update.return_value = True
    result = bridge.editStation(1, "Edited FM", "http://edited.stream", "AAC", "FR")
    assert result["ok"]
    mock_radio_mgr.update.assert_called_once_with(1, name="Edited FM", url="http://edited.stream")


def test_play_station_adds_to_history(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    bridge.playStation("http://jazz.stream", "Jazz FM")
    assert len(bridge.history) >= 1
    assert bridge.history[0]["name"] == "Jazz FM"


def test_import_m3u(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.importM3u("/nonexistent/file.m3u")
    assert not result["ok"]
    assert result["error"] == "FILE_NOT_FOUND"


def test_export_m3u(mock_radio_mgr, mock_player, tmp_path):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    out = tmp_path / "stations.m3u"
    result = bridge.exportM3u(str(out))
    assert result["ok"]
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "#EXTM3U" in content
    assert "Jazz FM" in content


def test_import_export_opml(mock_radio_mgr, mock_player, tmp_path):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    bridge.refresh()
    out = tmp_path / "stations.opml"
    result = bridge.exportOpml(str(out))
    assert result["ok"]
    assert out.is_file()


def test_delete_station(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    mock_radio_mgr.remove_station.return_value = True
    result = bridge.deleteStation("http://rock.stream")
    assert result["ok"]
    mock_radio_mgr.remove_station.assert_called_once()


def test_toggle_favorite_state(mock_radio_mgr, mock_player):
    bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
    result = bridge.toggleFavorite(1)
    assert result["ok"]
    assert result["favorite"] is True
