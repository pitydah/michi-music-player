"""E2E test: HTTP API with mock bridge."""
from unittest.mock import MagicMock
def test_e2e_http_api():
    from integrations.http_api.http_api import _MichiHandler
    h = _MichiHandler.__new__(_MichiHandler)
    h.path = "/api/player/play"
    h.headers = {"Content-Length": "0"}
    h.rfile = MagicMock()
    h.wfile = MagicMock()
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h._bridge = MagicMock()
    h._check_auth = MagicMock(return_value=True)
    h.do_POST()
    assert h.send_response.called
