import pytest
import os
from unittest.mock import MagicMock

from core.radio.models import (
    Station, AtomicMode,
)
from core.radio.import_export import (
    RadioImportService, RadioExportService, detect_playlist_format,
)


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.add.return_value = Station(
        id=1, name="Test", stream_url="https://example.com/stream",
    )
    repo.find_by_url.return_value = None
    repo.get_all_for_export.return_value = [
        Station(id=1, name="Radio 1", stream_url="https://r1.com/stream"),
        Station(id=2, name="Radio 2", stream_url="https://r2.com/stream"),
    ]
    repo.bulk_add.return_value = 2
    return repo


class TestDetectFormat:
    def test_detects_m3u8(self):
        assert detect_playlist_format("#EXTM3U\n#EXTINF:-1,Test\nhttp://example.com") == "m3u8"

    def test_detects_pls(self):
        assert detect_playlist_format("[playlist]\nFile1=http://example.com") == "pls"

    def test_detects_m3u(self):
        assert detect_playlist_format("#EXTINF:-1,Test\nhttp://example.com") == "m3u"

    def test_detects_json(self):
        assert detect_playlist_format('{"stations": []}') == "json"

    def test_detects_unknown(self):
        assert detect_playlist_format("not a playlist") == "unknown"


class TestImportM3U:
    def test_imports_m3u_with_extinf(self, mock_repo):
        svc = RadioImportService(mock_repo)
        content = "#EXTM3U\n#EXTINF:-1,Rock FM\nhttp://rock.fm/stream\n"
        result = svc.import_m3u(content)
        assert result.total_entries == 1

    def test_imports_m3u_without_extinf(self, mock_repo):
        svc = RadioImportService(mock_repo)
        content = "http://example.com/stream\n"
        result = svc.import_m3u(content)
        assert result.total_entries == 1

    def test_handles_empty_content(self, mock_repo):
        svc = RadioImportService(mock_repo)
        result = svc.import_m3u("")
        assert result.total_entries == 0

    def test_skips_comments(self, mock_repo):
        svc = RadioImportService(mock_repo)
        content = "# comment\nhttp://example.com/stream\n# another\n"
        result = svc.import_m3u(content)
        assert result.total_entries == 1

    def test_all_or_nothing_mode(self, mock_repo):
        svc = RadioImportService(mock_repo)
        content = "#EXTM3U\n#EXTINF:-1,A\nhttp://a.com\n#EXTINF:-1,B\nhttp://b.com\n"
        result = svc.import_m3u(content, AtomicMode.ALL_OR_NOTHING)
        assert result.imported > 0


class TestImportPLS:
    def test_imports_pls(self, mock_repo):
        svc = RadioImportService(mock_repo)
        content = "[playlist]\nFile1=http://example.com/stream\nTitle1=Test\nLength1=-1\nNumberOfEntries=1\nVersion=2\n"
        result = svc.import_pls(content)
        assert result.total_entries == 1
        mock_repo.add.assert_called()


class TestExportM3U8:
    def test_exports_m3u8(self, mock_repo, tmp_path):
        svc = RadioExportService(mock_repo)
        path = os.path.join(tmp_path, "radio.m3u8")
        result = svc.export_m3u8(path=path)
        assert result.ok is True
        assert result.count == 2
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "#EXTM3U" in content
        assert "Radio 1" in content
        assert "https://r1.com/stream" in content


class TestExportPLS:
    def test_exports_pls(self, mock_repo, tmp_path):
        svc = RadioExportService(mock_repo)
        path = os.path.join(tmp_path, "radio.pls")
        result = svc.export_pls(path=path)
        assert result.ok is True
        assert result.count == 2
        with open(path) as f:
            content = f.read()
        assert "[playlist]" in content
        assert "File1=https://r1.com/stream" in content


class TestExportJSON:
    def test_exports_json(self, mock_repo, tmp_path):
        svc = RadioExportService(mock_repo)
        path = os.path.join(tmp_path, "radio.json")
        result = svc.export_json(path=path)
        assert result.ok is True
        assert result.count == 2
        with open(path) as f:
            import json
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["name"] == "Radio 1"

    def test_export_invalid_path(self, mock_repo):
        svc = RadioExportService(mock_repo)
        result = svc.export_m3u8(path="")
        assert result.ok is False
        assert result.error != ""

    def test_export_nonexistent_dir(self, mock_repo):
        svc = RadioExportService(mock_repo)
        result = svc.export_m3u8(path="/nonexistent/radio.m3u8")
        assert result.ok is False
