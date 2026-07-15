"""Test RadioBridge import/export operations."""
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
    s1.tags = ["jazz"]
    s1.favorite = True
    s1.bitrate = 128
    s2 = MagicMock()
    s2.id = 2
    s2.name = "Rock FM"
    s2.url = "http://rock.stream"
    s2.codec = "AAC"
    s2.country = "UK"
    s2.tags = ["rock"]
    s2.favorite = False
    s2.bitrate = 256
    return [s1, s2]


@pytest.fixture
def mock_radio_mgr(mock_stations):
    mgr = MagicMock()
    mgr.get_all.return_value = mock_stations
    mgr.add.return_value = mock_stations[0]
    return mgr


@pytest.fixture
def mock_player():
    return MagicMock()


class TestImportM3u:
    def test_import_m3u_file_not_found(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u("/nonexistent/file.m3u")
        assert not result["ok"]
        assert result["error"] == "FILE_NOT_FOUND"

    def test_import_m3u_success(self, mock_radio_mgr, mock_player, tmp_path):
        m3u = tmp_path / "stations.m3u"
        m3u.write_text("#EXTM3U\n#EXTINF:-1,Jazz FM\nhttp://jazz.stream\nhttp://rock.stream\n")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u(str(m3u))
        assert result["ok"]
        assert result["count"] >= 2

    def test_import_m3u_empty_file(self, mock_radio_mgr, mock_player, tmp_path):
        m3u = tmp_path / "empty.m3u"
        m3u.write_text("")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u(str(m3u))
        assert result["ok"]
        assert result["count"] == 0

    def test_import_m3u_skips_comments(self, mock_radio_mgr, mock_player, tmp_path):
        m3u = tmp_path / "comments.m3u"
        m3u.write_text("#EXTM3U\n# comment line\nhttp://stream.url\n# another\nhttp://other.stream\n")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u(str(m3u))
        assert result["ok"]
        assert result["count"] == 2

    def test_import_m3u_ignores_non_http_lines(self, mock_radio_mgr, mock_player, tmp_path):
        m3u = tmp_path / "mixed.m3u"
        m3u.write_text("#EXTM3U\nhttp://valid.stream\n/path/to/file\nftp://invalid\nhttp://another.stream\n")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        result = bridge.importM3u(str(m3u))
        assert result["ok"]
        assert result["count"] == 2

    def test_import_m3u_no_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.importM3u("/some/file.m3u")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"


class TestExportM3u:
    def test_export_m3u_success(self, mock_radio_mgr, mock_player, tmp_path):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "export.m3u"
        result = bridge.exportM3u(str(out))
        assert result["ok"]
        assert out.is_file()
        content = out.read_text(encoding="utf-8")
        assert "#EXTM3U" in content
        assert "Jazz FM" in content
        assert "http://jazz.stream" in content

    def test_export_m3u_no_stations(self, mock_radio_mgr, mock_player, tmp_path):
        mock_radio_mgr.get_all.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "empty.m3u"
        result = bridge.exportM3u(str(out))
        assert not result["ok"]
        assert result["error"] == "NO_STATIONS"

    def test_export_m3u_triggers_refresh(self, mock_radio_mgr, mock_player, tmp_path):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "export.m3u"
        result = bridge.exportM3u(str(out))
        assert result["ok"]


class TestExportOpml:
    def test_export_opml_success(self, mock_radio_mgr, mock_player, tmp_path):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "stations.opml"
        result = bridge.exportOpml(str(out))
        assert result["ok"]
        assert out.is_file()
        content = out.read_text(encoding="utf-8")
        assert "<opml" in content
        assert "Jazz FM" in content

    def test_export_opml_no_stations(self, mock_radio_mgr, mock_player, tmp_path):
        mock_radio_mgr.get_all.return_value = []
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "empty.opml"
        result = bridge.exportOpml(str(out))
        assert not result["ok"]
        assert result["error"] == "NO_STATIONS"

    def test_export_opml_contains_all_stations(self, mock_radio_mgr, mock_player, tmp_path):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        out = tmp_path / "all.opml"
        result = bridge.exportOpml(str(out))
        assert result["ok"]
        content = out.read_text(encoding="utf-8")
        assert "Jazz FM" in content
        assert "Rock FM" in content

    def test_export_opml_failure(self, mock_radio_mgr, mock_player, tmp_path):
        mock_radio_mgr.get_all.side_effect = Exception("Export error")
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        out = tmp_path / "fail.opml"
        result = bridge.exportOpml(str(out))
        assert not result["ok"]


class TestSearch:
    def test_search_by_name(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.search(query="Jazz")
        assert result["ok"]
        assert result["count"] >= 1
        assert any(r["name"] == "Jazz FM" for r in result["results"])

    def test_search_by_country(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.search(query="", country="UK")
        assert result["ok"]
        assert result["count"] >= 1
        assert any(r["name"] == "Rock FM" for r in result["results"])

    def test_search_by_tag(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.search(tag="jazz")
        assert result["ok"]
        assert result["count"] >= 1

    def test_search_all(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.search()
        assert result["ok"]
        assert result["count"] == 2

    def test_search_no_results(self, mock_radio_mgr, mock_player):
        bridge = RadioBridge(radio_manager=mock_radio_mgr, player_service=mock_player)
        bridge.refresh()
        result = bridge.search(query="zzzznonexistent")
        assert result["ok"]
        assert result["count"] == 0

    def test_search_no_manager(self):
        bridge = RadioBridge(radio_manager=None, player_service=None)
        result = bridge.search(query="Jazz")
        assert not result["ok"]
        assert result["error"] == "NO_RADIO_MANAGER"
