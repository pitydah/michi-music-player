"""Tests for Micro Server — import real, HTTP mock, error handling."""
import json
from unittest.mock import patch, MagicMock



class TestMicroServerReal:
    def test_import_no_server_url(self):
        from core.micro_server_service import MicroServerService
        svc = MicroServerService()
        result = svc.import_tracks(["/test/a.flac"])
        assert not result["ok"]
        assert "NO_SERVER_URL" in result.get("error", "")

    def test_import_no_files(self):
        from core.micro_server_service import MicroServerService
        svc = MicroServerService()
        result = svc.import_tracks([], server_url="http://localhost:28700")
        assert result["ok"]
        assert result["imported"] == 0

    def test_import_file_not_found(self):
        from core.micro_server_service import MicroServerService
        svc = MicroServerService()
        result = svc.import_tracks(["/nonexistent/file.flac"],
                                   server_url="http://localhost:28700")
        assert result["failed"] == 1

    def test_import_sends_http(self, tmp_path):
        from core.micro_server_service import MicroServerService
        audio = tmp_path / "test_song.flac"
        audio.write_text("dummy flac content")

        svc = MicroServerService()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"ok": True}).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = svc.import_tracks([str(audio)],
                                       server_url="http://localhost:28700")
            assert result["ok"]
            assert result["imported"] == 1

    def test_import_http_error(self, tmp_path):
        from core.micro_server_service import MicroServerService
        audio = tmp_path / "test_song.flac"
        audio.write_text("dummy")

        svc = MicroServerService()

        import urllib.error
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                "http://localhost", 500, "Server Error", {}, None
            )
            result = svc.import_tracks([str(audio)],
                                       server_url="http://localhost:28700")
            assert result["failed"] == 1

    def test_import_connection_error(self, tmp_path):
        from core.micro_server_service import MicroServerService
        audio = tmp_path / "test.flac"
        audio.write_text("dummy")

        svc = MicroServerService()
        import urllib.error
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError(
                Exception("Connection refused")
            )
            result = svc.import_tracks([str(audio)],
                                       server_url="http://localhost:28700")
            assert result["failed"] == 1

    def test_import_album_fetches_from_db(self):
        from core.micro_server_service import MicroServerService
        from unittest.mock import MagicMock
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = [
            ("/test/track1.flac",), ("/test/track2.flac",)
        ]
        svc = MicroServerService(db=db)
        result = svc.import_album("album_key_123", server_url="http://localhost")
        # Should call import_tracks with the fetched files
        assert result["total"] == 2

    def test_health_with_db(self):
        from core.micro_server_service import MicroServerService
        svc = MicroServerService(db=MagicMock())
        health = svc.health()
        assert health["available"]

    def test_health_without_db(self):
        from core.micro_server_service import MicroServerService
        svc = MicroServerService()
        health = svc.health()
        assert not health["available"]
