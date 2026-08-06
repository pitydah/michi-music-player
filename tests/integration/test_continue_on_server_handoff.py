"""Integration: ContinueOnServerService handoff ordering (Slice 7).

The rule from ADR-002 / audit §9: local playback is NEVER paused until the
remote confirms PLAYING. These tests record the event order over HTTP against
a controlled fake server and assert the invariant:
  request handoff → server confirms playing → THEN local paused
and its negation: if the server rejects/never confirms, local never pauses.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from integrations.michi_link.client import RemoteServerInfo


class _EventRecorder:
    def __init__(self) -> None:
        self.events: list[str] = []
        self._lock = threading.Lock()

    def record(self, event: str) -> None:
        with self._lock:
            self.events.append(event)

    def order(self, *names: str) -> bool:
        with self._lock:
            positions = [self.events.index(n) for n in names if n in self.events]
            if len(positions) != len(names):
                return False
            return positions == sorted(positions)


class _FakeMicroServer:
    """Controlled fake: answers Michi Link v1 endpoints and records them."""

    def __init__(self, confirm_playing: bool = True):
        self._confirm_playing = confirm_playing
        self.events = _EventRecorder()
        self._httpd = HTTPServer(("127.0.0.1", 0), self._make_handler())
        self.port = int(self._httpd.server_address[1])
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, payload: dict, status: int = 200) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path = self.path.split("?")[0]
                if path == "/api/v1/playback/state":
                    server.events.record("remote_state_polled")
                    self._send({"state": "playing" if server._confirm_playing
                                else "stopped"})
                else:
                    self._send({"error": "not found"}, 404)

            def do_POST(self):
                path = self.path.split("?")[0]
                if path == "/api/v1/queue/transfer":
                    server.events.record("queue_transferred")
                    self._send({"ok": True, "transferred": 2})
                elif path == "/api/v1/queue/items":
                    server.events.record("queue_items")
                    self._send({"added": 2})
                elif path == "/api/v1/queue/jump":
                    server.events.record("queue_jump")
                    self._send({"ok": True})
                elif path == "/api/v1/playback/control":
                    body = json.loads(self.rfile.read(
                        int(self.headers.get("Content-Length", 0))) or b"{}")
                    if body.get("command") == "play":
                        server.events.record("remote_play_started")
                    self._send({"ok": True})
                elif path == "/api/v1/import/session/create":
                    server.events.record("session_created")
                    self._send({"session_id": "s1", "expires_at": 9999999999})
                else:
                    self._send({"error": "not found"}, 404)

        return Handler

    def _serve(self) -> None:
        self._httpd.serve_forever(poll_interval=0.05)

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5.0)


@pytest.fixture
def fake_server():
    server = _FakeMicroServer()
    yield server
    server.stop()


@pytest.fixture
def pause_log(fake_server):
    events = fake_server.events

    def pause_local():
        events.record("local_paused")

    return pause_local


def _server_info(fake_server) -> RemoteServerInfo:
    return RemoteServerInfo(
        host="127.0.0.1", port=fake_server.port,
        alias="FakeMicro", device_token="tok", device_id="player_d1",
    )


def test_local_paused_only_after_remote_confirmed(fake_server, pause_log) -> None:
    from integrations.michi_link.services.continue_on_server_service import (
        ContinueOnServerService,
    )
    svc = ContinueOnServerService(
        queue_provider=lambda: (["t1", "t2"], 0, 0.0),
        pause_local=pause_log,
    )
    result = svc.transfer_queue(_server_info(fake_server))
    assert result.ok
    # Order invariant: queue transferred → remote play started → state polled
    # (confirmed) → local paused. NEVER pause before confirmation.
    assert fake_server.events.order(
        "queue_transferred", "remote_play_started", "local_paused")
    assert "remote_state_polled" in fake_server.events.events
    paused_at = fake_server.events.events.index("local_paused")
    polled_at = fake_server.events.events.index("remote_state_polled")
    assert paused_at > polled_at, (
        "local playback was paused BEFORE the remote confirmed PLAYING"
    )


def test_local_never_paused_when_remote_never_confirms() -> None:
    server = _FakeMicroServer(confirm_playing=False)
    events = server.events
    paused = []

    def pause_local():
        paused.append(True)
        events.record("local_paused")

    from integrations.michi_link.services.continue_on_server_service import (
        ContinueOnServerService,
    )
    svc = ContinueOnServerService(
        queue_provider=lambda: (["t1", "t2"], 0, 0.0),
        pause_local=pause_local,
    )
    try:
        result = svc.transfer_queue(_server_info(server))
        assert result.ok  # queue transfer itself succeeded
        assert result.data["confirmed_playing"] is False
        assert "local_paused" not in events.events, (
            "local playback was paused although the remote never "
            "reported PLAYING"
        )
    finally:
        server.stop()


def test_local_never_paused_when_remote_rejects_transfer() -> None:
    """Server rejects the handoff: local stays untouched."""
    from integrations.michi_link.services.continue_on_server_service import (
        ContinueOnServerService,
    )
    server = _FakeMicroServer()
    paused = []
    events = server.events

    # Force a hard rejection: stop the server so every call fails fast.
    server.stop()

    svc = ContinueOnServerService(
        queue_provider=lambda: (["t1", "t2"], 0, 0.0),
        pause_local=lambda: paused.append(True),
    )
    result = svc.transfer_queue(_server_info(server))
    assert not result.ok
    assert paused == []
    assert "local_paused" not in events.events
