"""M11.3D — MPD protocol client tests (deterministic, no real MPD)."""

import socket
import threading

import pytest

from michi.infrastructure.audio_engines.mpd import (
    MpdProtocolError,
    _mpd_seconds_to_millis,
    _MpdProtocolClient,
    _quote_mpd_arg,
)


class _FakeMpdServer:
    """Servidor AF_UNIX de prueba: responde según guiones configurables."""

    def __init__(self, greeting="OK MPD 0.23.5\n", close_after_greeting=False):
        self.greeting = greeting
        self.close_after_greeting = close_after_greeting
        self.received: list[str] = []
        self.script: dict[str, str] = {}  # comando exacto → respuesta cruda
        self.close_after: set[str] = set()  # comandos que cierran tras responder
        self.sock_path = None
        self._thread = None
        self._server = None

    def __enter__(self):
        import tempfile

        self._tmp = tempfile.mkdtemp(prefix="mpdproto-")
        self.sock_path = f"{self._tmp}/test.sock"
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.sock_path)
        self._server.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.close()
        try:
            self._thread.join(timeout=2)
        finally:
            import shutil

            shutil.rmtree(self._tmp, ignore_errors=True)

    def _serve(self):
        conn, _ = self._server.accept()
        with conn:
            conn.sendall(self.greeting.encode("utf-8"))
            if self.close_after_greeting:
                return
            while True:
                data = conn.recv(4096)
                if not data:
                    return
                for line in data.decode("utf-8").splitlines():
                    self.received.append(line)
                    if line == "idle player":
                        # responder con un subsistema y bloquear hasta close
                        conn.sendall(b"player\nOK\n")
                        continue
                    response = self.script.get(line, "OK\n")
                    conn.sendall(response.encode("utf-8"))
                    if line in self.close_after:
                        return


@pytest.fixture
def fake_server():
    with _FakeMpdServer() as server:
        yield server


class TestProtocolConnection:
    def test_p1_valid_greeting(self, fake_server):
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        assert client.connected is True
        client.close()

    def test_p2_invalid_greeting_fails(self):
        with _FakeMpdServer(greeting="BOGUS\n") as server:
            client = _MpdProtocolClient(server.sock_path)
            with pytest.raises(MpdProtocolError, match="greeting"):
                client.connect()
            assert client.connected is False

    def test_p8_eof_before_greeting_fails(self):
        with _FakeMpdServer(greeting="", close_after_greeting=True) as server:
            client = _MpdProtocolClient(server.sock_path)
            with pytest.raises(MpdProtocolError, match="EOF"):
                client.connect()


class TestProtocolCommands:
    def test_p3_command_success_returns_fields(self, fake_server):
        fake_server.script["status"] = "volume: 70\nstate: play\nOK\n"
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        status = client.status()
        assert status == {"volume": "70", "state": "play"}
        assert fake_server.received == ["status"]
        client.close()

    def test_p4_ack_becomes_protocol_error(self, fake_server):
        fake_server.script["clear"] = "ACK [5@0] {clear} problems\n"
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        with pytest.raises(MpdProtocolError, match="ACK"):
            client.clear()
        client.close()

    def test_p5_addid_parses_id(self, fake_server):
        fake_server.script['addid "/m/a.flac"'] = "Id: 42\nOK\n"
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        assert client.addid("/m/a.flac") == 42
        assert fake_server.received == ['addid "/m/a.flac"']
        client.close()

    def test_p6_quoting_spaces_quotes_backslashes(self, fake_server):
        path = r'/m/weird "dir"\file.flac'
        fake_server.script['addid "/m/weird \\"dir\\"\\\\file.flac"'] = "Id: 7\nOK\n"
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        assert client.addid(path) == 7
        client.close()

    def test_p7_crlf_injection_rejected(self):
        with pytest.raises(MpdProtocolError, match="CR/LF"):
            _quote_mpd_arg("/m/a.flac\nclear")

    def test_p8_eof_mid_response_fails(self, fake_server):
        fake_server.script["status"] = "volume: 70\n"  # sin OK ni EOF limpio
        fake_server.close_after.add("status")
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        with pytest.raises(MpdProtocolError, match="EOF"):
            client.status()
        client.close()

    def test_idle_returns_changed_subsystems(self, fake_server):
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        assert client.idle("player") == ["player"]
        client.close()

    def test_seekid_fractional_seconds(self, fake_server):
        fake_server.script["seekid 7 1.234"] = "OK\n"
        client = _MpdProtocolClient(fake_server.sock_path)
        client.connect()
        client.seekid(7, 1.234)
        assert fake_server.received == ["seekid 7 1.234"]
        client.close()


class TestConversions:
    def test_elapsed_seconds_to_millis(self):
        assert _mpd_seconds_to_millis("1.5") == 1500
        assert _mpd_seconds_to_millis("0") == 0

    def test_fractional_precision_preserved(self):
        assert _mpd_seconds_to_millis("1.234") == 1234

    def test_invalid_and_negative_clamped(self):
        assert _mpd_seconds_to_millis("junk") == 0
        assert _mpd_seconds_to_millis("-5") == 0
