"""Tests for MPD Service Manager — mocked subprocess and os operations."""

from unittest.mock import patch


class TestMpdServiceManager:
    def test_is_installed_found(self):
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/mpd"
            from audio.mpd.mpd_service_manager import MpdServiceManager
            assert MpdServiceManager.is_installed() is True

    def test_is_installed_not_found(self):
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            from audio.mpd.mpd_service_manager import MpdServiceManager
            assert MpdServiceManager.is_installed() is False

    def test_running_initially_false(self):
        from audio.mpd.mpd_service_manager import MpdServiceManager
        mgr = MpdServiceManager()
        assert mgr.running is False

    def test_start_fails_when_not_installed(self):
        with patch("audio.mpd.mpd_service_manager.MpdServiceManager.is_installed") as mock_inst:
            mock_inst.return_value = False
            from audio.mpd.mpd_service_manager import MpdServiceManager
            mgr = MpdServiceManager()
            result = mgr.start("some_config")
            assert result is False

    def test_get_status(self):
        from audio.mpd.mpd_service_manager import MpdServiceManager
        with patch("audio.mpd.mpd_service_manager.MpdServiceManager.is_installed") as mock_inst:
            mock_inst.return_value = True
            mgr = MpdServiceManager()
            status = mgr.get_status()
            assert "installed" in status
            assert "running" in status
            assert status["installed"] is True

    def test_test_connection_failure(self):
        from audio.mpd.mpd_service_manager import MpdServiceManager
        from audio.mpd.mpd_errors import MpdConnectionError
        with patch("audio.mpd.mpd_client.MpdClient.connect") as mock_connect:
            mock_connect.side_effect = MpdConnectionError("refused")
            mgr = MpdServiceManager()
            ok, msg = mgr.test_connection()
            assert ok is False
            assert "refused" in msg
