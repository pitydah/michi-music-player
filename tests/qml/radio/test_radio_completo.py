from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge
from tests.qml.radio._svc_fixtures import station_dicts, make_radio_service_mock

pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_stations():
    return station_dicts()


@pytest.fixture
def mock_radio_mgr(mock_stations):
    return make_radio_service_mock(stations=mock_stations)


@pytest.fixture
def mock_player():
    p = MagicMock()
    p.play_url = MagicMock()
    p.stop = MagicMock()
    return p


@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestInitialState:
    def test_empty_on_create(self):
        b = RadioBridge()
        assert b.stations == []
        assert b.favorites == []
        assert b.history == []

    def test_no_radio_manager_fallback(self):
        b = RadioBridge()
        result = b.refresh()
        assert result["ok"] is True
        assert result["count"] == 0


class TestRefresh:
    def test_refresh_returns_ok(self, bridge):
        result = bridge.refresh()
        assert result["ok"] is True

    def test_refresh_populates_stations(self, bridge):
        bridge.refresh()
        assert len(bridge.stations) == 2

    def test_refresh_populates_favorites(self, bridge):
        bridge.refresh()
        assert len(bridge.favorites) == 1
        assert bridge.favorites[0]["name"] == "Jazz FM"

    def test_refresh_counts(self, bridge):
        result = bridge.refresh()
        assert result["count"] == 2

    def test_refresh_station_shape(self, bridge):
        bridge.refresh()
        s = bridge.stations[0]
        assert "id" in s and "name" in s and "url" in s


class TestAddStation:
    def test_add_station(self, bridge, mock_radio_mgr):
        result = bridge.addStation("New", "http://new", "MP3", "US")
        assert result["ok"] is True
        mock_radio_mgr.add_station.assert_called_once()

    def test_add_station_empty_url(self, bridge):
        result = bridge.addStation("X", "", "MP3", "US")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_URL"

    def test_add_station_no_manager(self):
        b = RadioBridge()
        result = b.addStation("X", "http://x", "", "")
        assert result["ok"] is False
        assert result["error"] == "NO_RADIO_MANAGER"


class TestPlayback:
    def test_play_station(self, bridge, mock_radio_mgr):
        result = bridge.playStation("http://jazz.stream", "Jazz FM")
        assert result["ok"] is True
        assert result["accepted"] is True
        mock_radio_mgr.play_station.assert_called_once_with(
            "http://jazz.stream", "Jazz FM")

    def test_play_station_empty_url(self, bridge):
        result = bridge.playStation("", "")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_URL"

    def test_play_station_no_manager(self):
        b = RadioBridge()
        result = b.playStation("http://x", "X")
        assert result["ok"] is False
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_play_not_playing_before_confirmation(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert bridge.isPlaying is False
        assert bridge.isBuffering is False  # no optimistic state

    def test_play_state_reflects_service_confirmation(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        assert bridge.isPlaying is False
        bridge._on_service_state_event({"state": "playing"})
        assert bridge.isPlaying is True
        assert bridge.isBuffering is False
        # History comes from the service, never fabricated by the bridge.
        assert len(bridge.history) == 0

    def test_stop_stream(self, bridge, mock_radio_mgr):
        result = bridge.stopStream()
        assert result["ok"] is True
        mock_radio_mgr.stop.assert_called_once()

    def test_cancel_stream(self, bridge, mock_radio_mgr):
        result = bridge.cancelStream()
        assert result["ok"] is True
        mock_radio_mgr.stop.assert_called_once()


class TestReconnectRetry:
    def test_reconnect_last(self, bridge, mock_player):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.reconnectLast()
        assert result["ok"] is True

    def test_reconnect_no_last(self, bridge):
        result = bridge.reconnectLast()
        assert result["ok"] is False
        assert result["error"] == "NO_LAST_STATION"

    def test_retry_current(self, bridge, mock_player):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        result = bridge.retryCurrent()
        assert result["ok"] is True


class TestDeleteEdit:
    def test_delete_station(self, bridge, mock_radio_mgr):
        bridge.refresh()
        result = bridge.deleteStation("http://rock.stream")
        assert result["ok"] is True
        mock_radio_mgr.delete_station.assert_called_once_with(2)

    def test_delete_station_no_manager(self):
        b = RadioBridge()
        result = b.deleteStation("http://x")
        assert result["ok"] is False
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_edit_station(self, bridge, mock_radio_mgr):
        result = bridge.editStation(1, "NewName", "http://new", "OGG", "FR")
        assert result["ok"] is True
        mock_radio_mgr.edit_station.assert_called_once_with(
            1, name="NewName", url="http://new", codec="OGG", country="FR")

    def test_edit_station_no_manager(self):
        b = RadioBridge()
        result = b.editStation(1, "X", "http://x")
        assert result["ok"] is False
        assert result["error"] == "NO_RADIO_MANAGER"


class TestFavorites:
    def test_toggle_favorite(self, bridge, mock_radio_mgr):
        result = bridge.toggleFavorite(1)
        assert result["ok"] is True
        assert result["favorite"] is True
        mock_radio_mgr.favorite_station.assert_called_once_with(1)

    def test_toggle_favorite_no_manager(self):
        b = RadioBridge()
        result = b.toggleFavorite(1)
        assert result["ok"] is False


class TestSearch:
    def test_search_by_query(self, bridge):
        result = bridge.search(query="Jazz")
        assert result["ok"] is True
        assert result["count"] >= 1

    def test_search_by_country(self, bridge):
        result = bridge.search(country="UK")
        assert result["ok"] is True
        assert result["count"] >= 1

    def test_search_no_match(self, bridge):
        result = bridge.search(query="NonExistent")
        assert result["count"] == 0

    def test_search_no_manager(self):
        b = RadioBridge()
        result = b.search(query="test")
        assert result["ok"] is False


class TestImportExport:
    def test_import_m3u(self, bridge, mock_radio_mgr, tmp_path):
        f = tmp_path / "test.m3u"
        f.write_text("#EXTM3U\n#EXTINF:-1,Test\nhttp://test.stream\n")
        result = bridge.importM3u(str(f))
        assert result["ok"] is True
        assert result["count"] >= 1

    def test_import_m3u_file_not_found(self, bridge):
        result = bridge.importM3u("/nonexistent/file.m3u")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_export_m3u(self, bridge, tmp_path):
        bridge.refresh()
        f = tmp_path / "export.m3u"
        result = bridge.exportM3u(str(f))
        assert result["ok"] is True

    def test_export_m3u_no_stations(self, bridge, tmp_path):
        b = RadioBridge()
        result = b.exportM3u(str(tmp_path / "empty.m3u"))
        assert result["ok"] is False
        assert result["error"] == "NO_STATIONS"

    def test_export_opml(self, bridge, tmp_path):
        bridge.refresh()
        f = tmp_path / "export.opml"
        result = bridge.exportOpml(str(f))
        assert result["ok"] is True

    def test_export_opml_no_stations(self, bridge, tmp_path):
        b = RadioBridge()
        result = b.exportOpml(str(tmp_path / "empty.opml"))
        assert result["ok"] is False


class TestMetadata:
    def test_get_metadata_unavailable(self, bridge):
        # The canonical service owns metadata; the bridge has no parallel client.
        result = bridge.getMetadata("http://example.com")
        assert result["ok"] is False
        assert result["error"] == "NO_METADATA"

    def test_get_metadata_no_manager(self):
        b = RadioBridge()
        result = b.getMetadata("http://x")
        assert result["ok"] is False


class TestStates:
    def test_connecting_state(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge._on_service_state_event({"state": "connecting"})
        assert bridge.isBuffering is True
        assert bridge.isPlaying is False

    def test_buffering_state(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge._on_service_state_event({"state": "buffering"})
        assert bridge.isBuffering is True

    def test_playing_state(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge._on_service_state_event({"state": "playing"})
        assert bridge.isPlaying is True

    def test_reconnecting_state(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge._on_service_state_event({"state": "reconnecting"})
        assert bridge.isBuffering is True
        assert bridge.isPlaying is False

    def test_stopped_state(self, bridge):
        result = bridge.stopStream()
        assert result["ok"] is True
        assert bridge.isPlaying is False

    def test_cancelling_state(self, bridge):
        result = bridge.cancelStream()
        assert result["ok"] is True

    def test_failed_state(self, bridge, mock_radio_mgr):
        mock_radio_mgr.play_station.return_value = {
            "ok": False, "error": "BACKEND_UNAVAILABLE"}
        result = bridge.playStation("http://fail", "")
        assert result["ok"] is False
        assert result["error"] == "BACKEND_UNAVAILABLE"
        assert bridge.isPlaying is False

    def test_failure_event_resets_playing(self, bridge):
        bridge.playStation("http://jazz.stream", "Jazz FM")
        bridge._on_service_state_event({"state": "playing"})
        assert bridge.isPlaying is True
        bridge._on_service_state_event({"state": "failed"})
        assert bridge.isPlaying is False
        assert bridge.isBuffering is False


class TestEdgeCases:
    def test_parse_playlist_m3u(self, bridge):
        content = "#EXTM3U\n#EXTINF:-1,Test\nhttp://test.radio\n"
        result = bridge.parsePlaylistFile(content)
        assert len(result) == 1
        assert result[0]["name"] == "Test"

    def test_parse_playlist_pls(self, bridge):
        content = "[playlist]\nFile1=http://aac.stream\nTitle1=My Station\n"
        result = bridge.parsePlaylistFile(content)
        assert len(result) == 1

    def test_parse_playlist_xspf(self, bridge):
        content = "<?xml?><playlist><trackList><track><title>X</title><location>http://x</location></track></trackList></playlist>"
        result = bridge.parsePlaylistFile(content)
        assert len(result) == 1

    def test_parse_playlist_empty(self, bridge):
        assert bridge.parsePlaylistFile("") == []

    def test_get_codec(self, bridge):
        codec = bridge.getCodec()
        assert codec == "" or codec == "MP3"

    def test_get_bitrate_default(self, bridge):
        assert bridge.getBitrate() == 0

    def test_playback_error_reports(self, bridge, mock_radio_mgr):
        mock_radio_mgr.play_station.return_value = {
            "ok": False, "error": "CONNECTION_FAILED"}
        result = bridge.playStation("http://fail", "Fail")
        assert result["ok"] is False
        assert result["error"] == "CONNECTION_FAILED"

    def test_delete_error_reports(self, bridge, mock_radio_mgr):
        bridge.refresh()
        mock_radio_mgr.delete_station.side_effect = RuntimeError("DB error")
        result = bridge.deleteStation("http://rock.stream")
        assert result["ok"] is False

    def test_import_m3u_no_manager(self):
        b = RadioBridge()
        result = b.importM3u("/some/file.m3u")
        assert result["ok"] is False

    def test_export_opml_no_manager(self):
        b = RadioBridge()
        result = b.exportOpml("/some/file.opml")
        assert result["ok"] is False

    def test_search_error_reports(self, bridge, mock_radio_mgr):
        mock_radio_mgr.search_stations.side_effect = RuntimeError("Search error")
        result = bridge.search(query="test")
        assert result["ok"] is False

    def test_edit_error_reports(self, bridge, mock_radio_mgr):
        mock_radio_mgr.edit_station.side_effect = RuntimeError("Update failed")
        result = bridge.editStation(1, "X", "http://x")
        assert result["ok"] is False

    def test_toggle_favorite_error_reports(self, bridge, mock_radio_mgr):
        mock_radio_mgr.favorite_station.side_effect = RuntimeError("Fav error")
        result = bridge.toggleFavorite(1)
        assert result["ok"] is False

    def test_remove_station_delegates_to_service(self, bridge, mock_radio_mgr):
        result = bridge.removeStation("2")
        assert result["ok"] is True
        mock_radio_mgr.delete_station.assert_called_once_with("2")
