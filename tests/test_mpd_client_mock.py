"""Tests for MpdClient with mocked socket methods."""

import pytest
from unittest.mock import MagicMock, patch


class TestMpdClientMock:
    def test_greeting_parsed_correctly(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient()
        with patch.object(client, '_read_line', return_value="OK MPD 0.23.12\n"):
            version = client._read_greeting()
            assert version == "0.23.12"

    def test_greeting_invalid_raises(self):
        from audio.mpd.mpd_client import MpdClient
        from audio.mpd.mpd_errors import MpdProtocolError
        client = MpdClient()
        with patch.object(client, '_read_line', return_value="INVALID\n"):
            with pytest.raises(MpdProtocolError, match="Invalid MPD greeting"):
                client._read_greeting()

    def test_greeting_empty_raises(self):
        from audio.mpd.mpd_client import MpdClient
        from audio.mpd.mpd_errors import MpdProtocolError
        client = MpdClient()
        with patch.object(client, '_read_line', return_value=None):
            with pytest.raises(MpdProtocolError, match="Empty MPD greeting"):
                client._read_greeting()

    def test_connect_sends_password_after_greeting(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient(password="secret", timeout=2.0)
        with patch.object(client, '_read_greeting', return_value="0.23.12"):
            with patch.object(client, '_read_ok', return_value=None):
                with patch.object(client, '_send_command') as mock_send:
                    with patch("audio.mpd.mpd_client.socket.create_connection") as mock_conn:
                        mock_conn.return_value = MagicMock()
                        client.connect()
                        assert client.connected is True
                        password_calls = [c[0][0] for c in mock_send.call_args_list
                                          if "password" in c[0][0]]
                        assert len(password_calls) == 1

    def test_connect_connection_refused_raises(self):
        from audio.mpd.mpd_client import MpdClient
        from audio.mpd.mpd_errors import MpdConnectionError
        with patch("audio.mpd.mpd_client.socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            client = MpdClient()
            with pytest.raises(MpdConnectionError):
                client.connect()

    def test_ping_returns_true(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient()
        client._sock = MagicMock()
        client._connected = True
        with patch.object(client, '_send_command'):
            with patch.object(client, '_read_ok', return_value=None):
                assert client.ping() is True

    def test_ping_returns_false_on_mpd_error(self):
        from audio.mpd.mpd_client import MpdClient
        from audio.mpd.mpd_errors import MpdConnectionError
        client = MpdClient()
        client._sock = MagicMock()
        client._connected = True
        with patch.object(client, '_send_command', side_effect=MpdConnectionError("fail")):
            assert client.ping() is False

    def test_ping_returns_false_on_oserror(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient()
        client._sock = MagicMock()
        client._connected = True
        with patch.object(client, '_send_command', side_effect=OSError("broken")):
            assert client.ping() is False

    def test_ensure_connected_when_not_connected(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient()
        with patch.object(client, 'connect') as mock_connect:
            client._connected = False
            client.ensure_connected()
            mock_connect.assert_called_once()

    def test_ensure_connected_when_already_connected(self):
        from audio.mpd.mpd_client import MpdClient
        client = MpdClient()
        client._connected = True
        with patch.object(client, 'connect') as mock_connect:
            client.ensure_connected()
            mock_connect.assert_not_called()
