"""Tests for MPD Discovery."""

from unittest.mock import patch


class TestMpdDiscovery:
    def test_find_local_mpd_empty(self):
        with patch("audio.mpd.mpd_client.MpdClient.connect") as mock_connect:
            from audio.mpd.mpd_errors import MpdConnectionError
            mock_connect.side_effect = MpdConnectionError("no connection")
            from audio.mpd.mpd_discovery import find_local_mpd
            results = find_local_mpd()
            assert results == []

    def test_find_mpd_processes_empty(self):
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_run.return_value = mock_result
            from audio.mpd.mpd_discovery import find_mpd_processes
            procs = find_mpd_processes()
            assert procs == []

    def test_format_discovery_report(self):
        from audio.mpd.mpd_discovery import format_discovery_report
        with patch("audio.mpd.mpd_discovery.find_local_mpd") as mock_local:
            mock_local.return_value = []
            with patch("audio.mpd.mpd_discovery.find_mpd_processes") as mock_procs:
                mock_procs.return_value = []
                report = format_discovery_report()
                assert "MPD Discovery" in report
                assert "No local MPD" in report
