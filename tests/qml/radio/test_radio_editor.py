"""Test RadioEditorDialog and RadioImportDialog logic for station management."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.radio_bridge import RadioBridge

pytestmark = [pytest.mark.qml_module("radio"),
              pytest.mark.qml_dimension("editor")]


@pytest.fixture
def mock_radio_mgr():
    mgr = MagicMock()
    mgr.add.return_value = MagicMock(id=99)
    mgr.update.return_value = True
    mgr.get_all.return_value = []
    return mgr


@pytest.fixture
def mock_player():
    return MagicMock()


@pytest.fixture
def bridge(mock_radio_mgr, mock_player):
    return RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)


class TestRadioEditor:
    """Test station add/edit operations."""

    def test_add_station(self, bridge, mock_radio_mgr):
        result = bridge.addStation("New FM", "http://new.stream", "MP3", "FR")
        assert result["ok"]
        mock_radio_mgr.add.assert_called_once_with(
            "New FM", "http://new.stream", country="FR", codec="MP3")

    def test_add_station_empty_url(self, bridge):
        result = bridge.addStation("Test", "", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "EMPTY_URL"

    def test_add_station_no_manager(self):
        b = RadioBridge(radio_manager=None, player_service=MagicMock())
        result = b.addStation("Test", "http://test.stream", "MP3", "")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_edit_station(self, bridge, mock_radio_mgr):
        mock_radio_mgr.update.return_value = True
        result = bridge.editStation(1, "Edited FM", "http://edited.stream", "AAC", "DE")
        assert result["ok"]
        mock_radio_mgr.update.assert_called_once_with(1, name="Edited FM", url="http://edited.stream")

    def test_edit_station_no_manager(self):
        b = RadioBridge(radio_manager=None, player_service=MagicMock())
        result = b.editStation(1, "Test", "http://test.stream")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_delete_station(self, bridge, mock_radio_mgr):
        mock_radio_mgr.remove_station.return_value = True
        result = bridge.deleteStation("http://delete.me")
        assert result["ok"]
        mock_radio_mgr.remove_station.assert_called_once_with("http://delete.me")

    def test_delete_station_no_manager(self):
        b = RadioBridge(radio_manager=None, player_service=MagicMock())
        result = b.deleteStation("http://test.stream")
        assert result["error"] == "NO_RADIO_MANAGER"

    def test_url_validation(self):
        import re
        pattern = re.compile(r"^(https?:\/\/)?[^\s]+$")
        assert pattern.match("http://valid.stream")
        assert pattern.match("https://valid.stream")
        assert not pattern.match("")
        assert not pattern.match("invalid url with spaces")

    def test_import_m3u(self, bridge, mock_radio_mgr, tmp_path):
        m3u = tmp_path / "test.m3u"
        m3u.write_text("#EXTM3U\n#EXTINF:-1,Jazz FM\nhttp://jazz.stream\n")
        result = bridge.importM3u(str(m3u))
        assert result["ok"]
        assert result["count"] >= 1

    def test_import_m3u_not_found(self, bridge):
        result = bridge.importM3u("/nonexistent/file.m3u")
        assert not result["ok"]
        assert result["error"] == "FILE_NOT_FOUND"

    def test_export_m3u(self, bridge, tmp_path):
        bridge.refresh()
        out = tmp_path / "export.m3u"
        result = bridge.exportM3u(str(out))
        assert result["ok"] or out.exists()

    def test_export_opml(self, bridge, tmp_path):
        bridge.refresh()
        out = tmp_path / "export.opml"
        result = bridge.exportOpml(str(out))
        assert result["ok"] or out.exists()

    def test_export_empty(self, tmp_path):
        b = RadioBridge(radio_manager=MagicMock(), player_service=MagicMock())
        b.refresh()
        out = tmp_path / "empty.m3u"
        result = b.exportM3u(str(out))
        assert not result["ok"]
        assert result["error"] == "NO_STATIONS"

    def test_add_with_country_code(self, bridge, mock_radio_mgr):
        result = bridge.addStation("Deutschlandfunk", "http://dradio.stream", "MP3", "DE")
        assert result["ok"]
        call_args = mock_radio_mgr.add.call_args
        assert call_args[0][0] == "Deutschlandfunk"
        assert call_args[1] == "http://dradio.stream"
