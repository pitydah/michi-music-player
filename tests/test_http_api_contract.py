"""Test HTTP API contract - verify responses are structured correctly."""
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_handler():
    from integrations.http_api.http_api import _MichiHandler

    class FakeHandler(_MichiHandler):
        def __init__(self):
            self.path = "/api/player/play"
            self.headers = {"Content-Length": "0"}
            self.rfile = MagicMock()
            self.rfile.read.return_value = b"{}"
            self.wfile = MagicMock()
            self.send_response = MagicMock()
            self.send_header = MagicMock()
            self.end_headers = MagicMock()
            self._bridge = MagicMock()
            self._store = MagicMock()
            self._store.player_snapshot.return_value = {}
            self._token = ""
            self._db = MagicMock()
            self._check_auth = MagicMock(return_value=True)

    def player_snapshot(self):
        return {}

    return FakeHandler()


def _get_status(mock_handler):
    args, _ = mock_handler.send_response.call_args
    return args[0]


def test_play_returns_200(mock_handler):
    handler = mock_handler
    handler.path = "/api/player/play"
    handler.do_POST()
    assert handler.send_response.called
    assert _get_status(handler) == 200


def test_pause_returns_200(mock_handler):
    handler = mock_handler
    handler.path = "/api/player/pause"
    handler.do_POST()
    assert handler.send_response.called
    assert _get_status(handler) == 200


def test_unknown_path_returns_404(mock_handler):
    handler = mock_handler
    handler.path = "/api/unknown"
    handler.do_POST()
    assert _get_status(handler) == 404


def test_no_bridge_returns_503(mock_handler):
    handler = mock_handler
    handler._bridge = None
    handler.path = "/api/player/play"
    handler.do_POST()
    assert _get_status(handler) == 503
