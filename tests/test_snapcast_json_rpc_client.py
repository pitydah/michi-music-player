import json
import socket

import pytest

from integrations.snapcast.json_rpc_client import HomeAudioError, SnapcastJsonRpcClient


class FakeSocket:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, _timeout):
        return None

    def sendall(self, payload):
        self.sent.append(payload)

    def recv(self, _size):
        return self.responses.pop(0) if self.responses else b""


def response(request_id=1, result=None):
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result or {}}).encode() + b"\r\n"


def test_rpc_frames_requests_and_increments_ids(monkeypatch):
    sockets = [FakeSocket([response(1)]), FakeSocket([response(2)])]
    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: sockets.pop(0))
    client = SnapcastJsonRpcClient(timeout=0.1)

    assert client.get_status() == {}
    assert client.get_status() == {}
    assert client.connected is True


def test_rpc_rejects_empty_error_and_wrong_id(monkeypatch):
    cases = [
        (b"", "EMPTY_RESPONSE"),
        (json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -1}}).encode() + b"\n", "RPC_ERROR"),
        (response(99), "RESPONSE_ID_MISMATCH"),
    ]
    for payload, code in cases:
        fake = FakeSocket([payload])
        monkeypatch.setattr(
            socket,
            "create_connection",
            lambda *_args, _fake=fake, **_kwargs: _fake,
        )
        client = SnapcastJsonRpcClient(timeout=0.1)
        with pytest.raises(HomeAudioError) as error:
            client.get_status()
        assert error.value.code == code
        assert client.connected is False


def test_rpc_reports_timeout(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise socket.timeout("late")

    monkeypatch.setattr(socket, "create_connection", timeout)
    with pytest.raises(HomeAudioError) as error:
        SnapcastJsonRpcClient(timeout=0.01).get_status()
    assert error.value.code == "TIMEOUT"
