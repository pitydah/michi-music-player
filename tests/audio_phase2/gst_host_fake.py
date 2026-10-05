#!/usr/bin/env python
"""Deterministic test double for the GStreamer output host process.

Not production code. Exposes scripted behaviors (hang/crash/garbage/...)
so the supervisor's parent-side deadlines, termination ladder and generation
fences can be proven WITHOUT relying on the real GStreamer deadlock.

Usage: python gst_host_fake.py --fd N --behavior <behavior>
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import struct
import sys
import time

from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
    GST_HOST_PROTOCOL_VERSION,
    FrameDecoder,
    HostOperation,
    HostProtocolError,
    MessageKind,
    encode_message,
    make_message,
)

FAKE_HELLO = {
    "protocol_version": GST_HOST_PROTOCOL_VERSION,
    "python_version": "fake",
    "pid": os.getpid(),
    "gstreamer_version": "GStreamer fake-1.0",
    "playbin3_available": True,
    "runtime_failure": None,
}


class FakeHost:
    def __init__(self, channel: socket.socket, behavior: str) -> None:
        self._channel = channel
        self._behavior = behavior
        self._decoder = FrameDecoder()
        self._host_generation = 0
        self._hang_operation = (
            behavior.split(":", 1)[1] if behavior.startswith("hang_on:") else None
        )

    def serve(self) -> int:
        if self._behavior == "crash":
            return 7
        if self._behavior == "garbage":
            self._channel.sendall(b"\x00\x00\x00\x08not json")
            time.sleep(30)
            return 0
        if self._behavior == "oversized":
            self._channel.sendall(struct.pack(">I", 10**9) + b"x")
            time.sleep(30)
            return 0
        if self._behavior == "ignore_sigterm":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if self._behavior == "hang_on_shutdown_ignore_term":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            self._hang_operation = "shutdown"
        while True:
            try:
                chunk = self._channel.recv(65536)
            except OSError:
                return 2
            if not chunk:
                return 0
            try:
                frames = self._decoder.feed(chunk)
            except HostProtocolError:
                return 3
            for frame in frames:
                if (
                    self._behavior == "malformed_response"
                    and frame.get("operation") != HostOperation.HELLO.value
                ):
                    self._channel.sendall(b"\x00\x00\x00\x04nope")
                    continue
                result = self._route(frame)
                if result is not None:
                    return result

    def _route(self, frame: dict) -> int | None:
        self._host_generation = int(frame.get("host_generation", 0))
        if frame["kind"] != MessageKind.COMMAND.value:
            return None
        request_id = frame.get("request_id")
        operation = frame.get("operation")
        if operation == HostOperation.HELLO.value:
            if self._behavior == "no_hello":
                return None
            if self._behavior == "wrong_version":
                payload = dict(FAKE_HELLO)
                payload["protocol_version"] = 999
                self._send_raw_json(
                    {
                        **make_message(MessageKind.HELLO, request_id=request_id),
                        "protocol_version": 999,
                        "payload": payload,
                    }
                )
                return None
            self._respond(MessageKind.HELLO, request_id, FAKE_HELLO)
            if self._behavior == "wrong_event_generation":
                stale = make_message(
                    MessageKind.EVENT,
                    host_generation=self._host_generation + 1,
                    payload={"event": "host_heartbeat", "tick": 1},
                )
                self._channel.sendall(encode_message(stale))
                current = make_message(
                    MessageKind.EVENT,
                    host_generation=self._host_generation,
                    payload={"event": "host_heartbeat", "tick": 2},
                )
                self._channel.sendall(encode_message(current))
            return None
        if self._behavior == "crash_after_ack":
            return 7
        if self._hang_operation is not None and operation == self._hang_operation:
            while True:
                time.sleep(1)
        if self._behavior == "drop_response":
            return None
        if self._behavior == "slow":
            time.sleep(0.3)
        if (
            operation == HostOperation.SHUTDOWN.value
            and self._behavior != "hang_on:shutdown"
        ):
            self._respond(
                MessageKind.SHUTDOWN_COMPLETE,
                request_id,
                {"termination": "GRACEFUL"},
            )
            return 0
        if operation == HostOperation.PING.value:
            self._respond(
                MessageKind.RESULT,
                request_id,
                {"pong": True, "host_generation": self._host_generation},
            )
            return None
        generation = self._host_generation
        if self._behavior == "wrong_response_generation":
            generation += 1
        self._respond_result(request_id, generation)
        return None

    def _respond(
        self, kind: MessageKind, request_id: str | None, payload: dict
    ) -> None:
        frame = make_message(
            kind,
            host_generation=self._host_generation,
            request_id=request_id,
            payload=payload,
        )
        self._channel.sendall(encode_message(frame))

    def _respond_result(self, request_id: str | None, generation: int) -> None:
        frame = make_message(
            MessageKind.RESULT,
            host_generation=generation,
            request_id=request_id,
            payload={"ok": True},
        )
        self._channel.sendall(encode_message(frame))

    def _send_raw_json(self, frame: dict) -> None:
        import json

        body = json.dumps(frame).encode("utf-8")
        self._channel.sendall(struct.pack(">I", len(body)) + body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fd", type=int, required=True)
    parser.add_argument("--behavior", default="normal")
    args = parser.parse_args(argv)
    channel = socket.socket(fileno=args.fd)
    channel.setblocking(True)
    return FakeHost(channel, args.behavior).serve()


if __name__ == "__main__":
    sys.exit(main())
