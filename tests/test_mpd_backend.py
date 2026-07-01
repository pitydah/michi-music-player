"""Tests for MpdBackend — uses mocked MpdClient."""

import pytest
from unittest.mock import MagicMock, patch


class TestMpdBackend:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.connected = False
        return client

    @pytest.fixture
    def backend(self, mock_client):
        from audio.backends.mpd_backend import MpdBackend
        with patch("audio.backends.mpd_backend.MpdClient") as MockMpdClient:
            MockMpdClient.return_value = mock_client
            b = MpdBackend()
            b._client = mock_client
            return b

    def test_backend_id(self, backend):
        assert backend.backend_id == "mpd"

    def test_capabilities(self, backend):
        caps = backend.capabilities
        assert caps.supports_bitperfect is True
        assert caps.supports_dsd is True
        assert caps.supports_dop is True
        assert caps.supports_remote is True
        assert caps.supports_digital_volume is False

    def test_connect(self, backend, mock_client):
        backend.connect()
        mock_client.connect.assert_called_once()

    def test_disconnect(self, backend, mock_client):
        backend.disconnect()
        mock_client.disconnect.assert_called_once()

    def test_play_clears_and_adds(self, backend, mock_client):
        backend.play("/home/user/Music/Album/track.flac")
        mock_client.clear.assert_called_once()
        mock_client.add.assert_called_once()
        mock_client.playpos.assert_called_once_with(0)

    def test_pause(self, backend, mock_client):
        backend.pause()
        mock_client.pause.assert_called_once_with(1)

    def test_resume(self, backend, mock_client):
        backend.resume()
        mock_client.pause.assert_called_once_with(0)

    def test_stop(self, backend, mock_client):
        backend.stop()
        mock_client.stop.assert_called_once()

    def test_seek(self, backend, mock_client):
        backend.seek(45.0)
        mock_client.seekcur.assert_called_once_with(45.0)

    def test_set_volume_blocked(self, backend, mock_client):
        from audio.backends.errors import BackendCapabilityError
        with pytest.raises(BackendCapabilityError, match="Volumen digital"):
            backend.set_volume(50)
        mock_client.setvol.assert_not_called()

    def test_set_queue(self, backend, mock_client):
        backend.set_queue(["a.flac", "b.flac"], start_index=1)
        mock_client.clear.assert_called_once()
        assert mock_client.add.call_count == 2
        mock_client.playpos.assert_called_once_with(1)

    def test_clear_queue(self, backend, mock_client):
        backend.clear_queue()
        mock_client.clear.assert_called_once()

    def test_get_snapshot_disconnected(self, backend, mock_client):
        from audio.mpd.mpd_errors import MpdConnectionError
        mock_client.status.side_effect = MpdConnectionError("no connection")
        snap = backend.get_snapshot()
        assert snap.state == "error"
        assert "connection lost" in snap.error

    def test_get_diagnostics_disconnected(self, backend, mock_client):
        from audio.mpd.mpd_errors import MpdConnectionError
        mock_client.status.side_effect = MpdConnectionError("no connection")
        diag = backend.get_diagnostics()
        assert diag.bitperfect_status == "not_connected"

    def test_shutdown(self, backend, mock_client):
        mock_client.connected = True
        backend.shutdown()
        mock_client.stop.assert_called_once()
        mock_client.disconnect.assert_called_once()

    def test_mapped_queue_paths(self, backend, mock_client):
        from audio.mpd.mpd_path_mapper import MpdPathMapper
        mapper = MpdPathMapper(
            music_dir="/home/user/Music",
            local_root="/home/user/Music")
        backend._mapper = mapper
        backend.set_queue(["/home/user/Music/A/track.flac"],
                          start_index=0)
        args = mock_client.add.call_args[0]
        assert args[0] == "A/track.flac"
