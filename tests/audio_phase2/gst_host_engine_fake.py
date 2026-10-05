#!/usr/bin/env python
"""Host process script for hosted-port tests: real host main + fake engine.

Not production code: exercises the production host session/command dispatch
with a scripted engine port, so the parent proxy can be tested
deterministically without GStreamer.

Usage: python gst_host_engine_fake.py --fd N --engine-behavior <behavior>
"""

from __future__ import annotations

import argparse
import socket
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])  # script dir for the fake port

from host_engine_fakes import FakeEnginePort  # noqa: E402

from michi.infrastructure.audio_engines.gstreamer_host_process import (  # noqa: E402
    GStreamerHostMain,
)


class _FakeRuntime:
    def describe(self) -> dict:
        return {
            "protocol_version": 1,
            "python_version": "fake",
            "pid": __import__("os").getpid(),
            "gstreamer_version": "GStreamer fake-1.0",
            "playbin3_available": True,
            "runtime_failure": None,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fd", type=int, required=True)
    parser.add_argument("--engine-behavior", default="normal")
    args = parser.parse_args(argv)
    channel = socket.socket(fileno=args.fd)
    channel.setblocking(True)
    return GStreamerHostMain(
        channel,
        engine_port_factory=lambda coordinator: FakeEnginePort(
            args.engine_behavior, coordinator
        ),
        runtime=_FakeRuntime(),
    ).serve()


if __name__ == "__main__":
    sys.exit(main())
